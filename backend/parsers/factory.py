import pdfplumber
import re
import io
from parsers.base import ParserBase, LancamentoBase
from typing import List


class ParserBB(ParserBase):

    IGNORAR_RE = re.compile(
        r"^saldo|s\s*a\s*l\s*d\s*o|total aplic|sujeito|transação efetuada|"
        r"valide no app|recebeu cobran|bb\.com\.br|https?://|"
        r"cliente\b|agência:|conta:|lançamentos$|dia\s+lote|"
        r"00/00/0000|rende facil|^\*\s*saldo|total aplicações|"
        r"^\s*$",
        re.IGNORECASE
    )

    # Valor modelo 1: termina com (+ ou -)
    VALOR_M1_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2})\s*\(([+-])\)\s*$")
    # Valor modelo 2: termina com C ou D
    VALOR_M2_RE = re.compile(
        r"(\d{1,3}(?:\.\d{3})*,\d{2})\s+([CD])"
        r"(?:\s+\d{1,3}(?:\.\d{3})*,\d{2}\s+[CD])?$"
    )

    # Extrato em .txt (colunas de largura fixa): Data / Lançamento /
    # Detalhes / Nº documento / Valor / Tipo Lançamento. Posições
    # baseadas no cabeçalho real do arquivo (mesmo texto/estrutura do
    # extrato em PDF, só que exportado em texto puro em vez de PDF).
    TXT_VALOR_RE = re.compile(r"(-?\d{1,3}(?:\.\d{3})*,\d{2})\s+([CD])")
    _TXT_COL_DATA = (0, 20)
    _TXT_COL_LANCAMENTO = (20, 55)
    _TXT_COL_DETALHES = (55, 105)
    _TXT_COL_VALOR = (135, 163)

    def parse(self, conteudo: bytes) -> List[LancamentoBase]:
        if conteudo[:4] == b"%PDF":
            with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
                texto_total = "\n".join(
                    p.extract_text(x_tolerance=3, y_tolerance=3) or "" for p in pdf.pages
                )
                # Extrato "Autoatendimento" (autoatendimento2.bb.com.br,
                # ApjExtratoContaCorrente) — checa ANTES do modelo 2, porque
                # esse formato também termina os valores em C/D e cairia
                # errado no modelo 2 (que é linha-a-linha e não dá conta da
                # tabela real desse formato).
                if "ApjExtratoContaCorrente" in texto_total or re.search(
                    r"AG\.?\s*\n?\s*ORIGEM", texto_total, re.IGNORECASE
                ):
                    return self._parse_modelo3(pdf)
            if re.search(r"\d{1,3}(?:\.\d{3})*,\d{2}\s+[CD]\b", texto_total):
                return self._parse_modelo2(texto_total.splitlines())
            else:
                return self._parse_modelo1(texto_total.splitlines())
        else:
            # não é PDF (não começa com %PDF) — assume extrato em .txt
            return self._parse_txt(conteudo)

    def _parse_txt(self, conteudo: bytes) -> List[LancamentoBase]:
        texto = conteudo.decode("utf-8", errors="ignore")
        resultado = []

        for linha in texto.splitlines():
            if not linha.strip():
                continue

            data = linha[self._TXT_COL_DATA[0]:self._TXT_COL_DATA[1]].strip()
            if not re.match(r"^\d{2}/\d{2}/\d{4}$", data):
                continue  # pula cabeçalho e qualquer linha sem data no início

            lancamento = linha[self._TXT_COL_LANCAMENTO[0]:self._TXT_COL_LANCAMENTO[1]].strip()
            # linha de saldo (não é lançamento de verdade) — compara sem
            # espaço nenhum, porque o saldo final do arquivo vem escrito
            # como "S A L D O" (letra por letra), diferente do "Saldo
            # Anterior"/"Saldo do dia" do meio do extrato
            lancamento_sem_espaco = lancamento.replace(" ", "").lower()
            if lancamento_sem_espaco in ("saldoanterior", "saldododia", "saldo"):
                continue

            detalhes = linha[self._TXT_COL_DETALHES[0]:self._TXT_COL_DETALHES[1]].strip()
            valor_campo = linha[self._TXT_COL_VALOR[0]:self._TXT_COL_VALOR[1]].strip()

            m_val = self.TXT_VALOR_RE.search(valor_campo)
            if not m_val:
                continue

            valor_str, indicador = m_val.group(1), m_val.group(2)
            try:
                valor = float(valor_str.replace(".", "").replace(",", "."))
            except ValueError:
                continue
            # o texto já costuma vir com o "-" no débito; isso aqui é só
            # uma garantia extra, caso o sinal não venha explícito
            if indicador == "D" and valor > 0:
                valor = -valor

            historico = f"{lancamento} - {detalhes}" if detalhes else lancamento
            resultado.append(LancamentoBase(data[:5], historico, valor, self.conta_banco))

        return resultado

    def _parse_modelo1(self, linhas: List[str]) -> List[LancamentoBase]:
        resultado = []
        n = len(linhas)
        linhas_consumidas: set = set()

        for i, linha in enumerate(linhas):
            linha = linha.strip()

            
            m_val = self.VALOR_M1_RE.search(linha)
            if not m_val:
                continue

            valor_str = m_val.group(1)
            sinal = m_val.group(2)

            
            if re.search(r"saldo", linha, re.IGNORECASE):
                continue

            data = None
            if i >= 1:
                prev = linhas[i - 1].strip()
                m_d = re.match(r"^(\d{2}/\d{2}/\d{4})\s*$", prev)
                if m_d:
                    data = m_d.group(1)[:5]

            if data is None and i >= 2:
                prev2 = linhas[i - 2].strip()
                m_d = re.match(r"^(\d{2}/\d{2}/\d{4})\s*$", prev2)
                if m_d:
                    data = m_d.group(1)[:5]

            if data is None and i >= 1:
                prev = linhas[i - 1].strip()
                m_d = re.match(r"^(\d{2}/\d{2}/\d{4})\s+.+", prev)
                if m_d:
                    data = m_d.group(1)[:5]

            if data is None:
                continue

            historico = self._historico_modelo1(linhas, i, linhas_consumidas)
            if not historico or self.IGNORAR_RE.search(historico):
                continue

            try:
                valor = float(valor_str.replace(".", "").replace(",", "."))
                if sinal == "-":
                    valor = -valor
            except ValueError:
                continue

            resultado.append(LancamentoBase(data, historico, valor, self.conta_banco))

        return resultado

    def _historico_modelo1(self, linhas: List[str], i_valor: int, linhas_consumidas: set) -> str:

        linha_val = linhas[i_valor].strip()
        m_val_local = self.VALOR_M1_RE.search(linha_val)
        texto_antes_valor = linha_val[:m_val_local.start()].strip()

        detalhe_embutido = re.sub(r"^(?:[\d.]{4,}\s+){0,3}", "", texto_antes_valor).strip()
        detalhe_embutido = re.sub(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", "", detalhe_embutido).strip()
        if re.match(r"^[\d\s./\-]*$", detalhe_embutido):
            detalhe_embutido = ""

        rotulo = None
        for delta in [1, 2]:
            idx = i_valor - delta
            if idx < 0:
                continue
            cand = linhas[idx].strip()
            if not cand or self.IGNORAR_RE.search(cand):
                continue

            if self.VALOR_M1_RE.search(cand):
                continue
            
            if idx in linhas_consumidas:
                continue
            if re.match(r"^\d{2}/\d{2}/\d{4}\s*$", cand):
                continue
            m = re.match(r"^\d{2}/\d{2}/\d{4}\s+(.+)", cand)
            if m:
                rotulo = m.group(1).strip()
                break
            if re.match(r"^[\d\s./\-]+$", cand):
                continue
            rotulo = cand
            break

        if rotulo is None:

            rotulo = detalhe_embutido or texto_antes_valor
            detalhe_embutido = ""

        historico = rotulo
        if detalhe_embutido:
            historico = f"{historico} - {detalhe_embutido}"
        elif i_valor + 1 < len(linhas):
           
            prox = linhas[i_valor + 1].strip()
            eh_novo_lancamento = re.match(r"^\d{2}/\d{2}/\d{4}\s*$", prox) or \
                re.match(r"^\d{2}/\d{2}/\d{4}\s+.+", prox)
            if (prox and not self.IGNORAR_RE.search(prox)
                    and not eh_novo_lancamento
                    and not self.VALOR_M1_RE.search(prox)):
                historico = f"{historico} - {prox}"
                linhas_consumidas.add(i_valor + 1)

    def _parse_modelo3(self, pdf) -> List[LancamentoBase]:
        """
        Extrato "Autoatendimento" do BB (autoatendimento2.bb.com.br,
        ApjExtratoContaCorrente) — é uma tabela de verdade (renderizada de
        HTML pra PDF), sem grade vertical entre colunas, só linhas
        horizontais finas separando cada lançamento.

        Não dá pra usar extract_text() linha a linha aqui: as colunas
        DATA/AG.ORIGEM/LOTE/DOCUMENTO/VALOR ficam centralizadas na altura
        do texto de HISTÓRICO (que ocupa de 1 a 3 linhas dependendo do
        lançamento), então a ordem das linhas no texto extraído não bate
        com a ordem visual da tabela — o texto do "tipo" (ex.: "Compra com
        Cartão") sai ANTES da linha com a data, e o resto do detalhe sai
        DEPOIS, intercalado com o próximo lançamento.

        Em vez disso, usa as retas finas (rects com altura < 2pt) que
        desenham cada linha da tabela: a posição X de cada segmento dá o
        limite de cada coluna (constante em todas as páginas), e a posição
        Y de cada reta dá o início/fim da faixa vertical de cada
        lançamento (que pode ter 1 a 3 linhas de altura). Dentro de cada
        faixa, agrupa as palavras por coluna (bounding box) e por linha
        dentro da coluna, pra reconstruir o texto igual ele aparece na
        tela.
        """
        resultado = []
        ultima_data = None

        for page in pdf.pages:
            finas = [r for r in page.rects if (r["bottom"] - r["top"]) < 2]
            if not finas:
                continue

            xs = sorted(set(round(r["x0"], 1) for r in finas))
            borda_direita = max(r["x1"] for r in finas)
            limites_coluna = xs + [borda_direita]
            if len(limites_coluna) < 3:
                continue

            topos = sorted(set(round(r["top"], 1) for r in finas))
            if len(topos) < 2:
                continue

            palavras = page.extract_words(x_tolerance=2, y_tolerance=2, keep_blank_chars=False)

            for i in range(len(topos) - 1):
                y0, y1 = topos[i], topos[i + 1]
                palavras_linha = [
                    w for w in palavras if y0 - 0.5 <= w["top"] < y1 - 0.5
                ]
                if not palavras_linha:
                    continue

                colunas = [[] for _ in range(len(limites_coluna) - 1)]
                for w in palavras_linha:
                    for c in range(len(limites_coluna) - 1):
                        if limites_coluna[c] - 1 <= w["x0"] < limites_coluna[c + 1] - 1:
                            colunas[c].append(w)
                            break

                data_txt = self._m3_texto_coluna(colunas, 0)
                # coluna 3 = HISTÓRICO (0=DATA, 1=AG.ORIGEM, 2=LOTE,
                # 3=HISTÓRICO, 4=DOCUMENTO, 5=VALOR)
                historico_txt = self._m3_texto_coluna(colunas, 3) if len(colunas) > 3 else ""
                valor_txt = self._m3_texto_coluna(colunas, 5) if len(colunas) > 5 else ""

                if re.match(r"^\d{2}/\d{2}/\d{4}$", data_txt):
                    ultima_data = data_txt[:5]

                if not historico_txt or self.IGNORAR_RE.search(historico_txt):
                    continue
                if ultima_data is None:
                    continue

                m_val = re.search(r"(\d{1,3}(?:\.\d{3})*,\d{2})\s*([CD])?", valor_txt)
                if not m_val:
                    continue

                valor_str, indicador = m_val.group(1), m_val.group(2)
                try:
                    valor = float(valor_str.replace(".", "").replace(",", "."))
                except ValueError:
                    continue
                if indicador == "D":
                    valor = -valor

                resultado.append(LancamentoBase(ultima_data, historico_txt, valor, self.conta_banco))

        return resultado

    @staticmethod
    def _m3_texto_coluna(colunas: list, idx: int) -> str:
        """Junta as palavras de uma coluna, agrupando por linha (baseado na
        proximidade de 'top') e juntando as linhas com ' - ', na mesma
        convenção usada no resto do histórico deste parser."""
        ws = sorted(colunas[idx], key=lambda w: (round(w["top"]), w["x0"]))
        linhas: list = []
        atual_top = None
        buffer: list = []
        for w in ws:
            t = round(w["top"])
            if atual_top is None or abs(t - atual_top) <= 2:
                buffer.append(w["text"])
                atual_top = t if atual_top is None else atual_top
            else:
                linhas.append(" ".join(buffer))
                buffer = [w["text"]]
                atual_top = t
        if buffer:
            linhas.append(" ".join(buffer))
        return " - ".join(l.strip() for l in linhas if l.strip())

        historico = historico.strip(" -")
        return historico if len(historico) > 3 else texto_antes_valor

    def _parse_modelo2(self, linhas: List[str]) -> List[LancamentoBase]:
        resultado = []
        i = 0
        while i < len(linhas):
            linha = linhas[i].strip()
            i += 1

            if self.IGNORAR_RE.search(linha):
                continue

            m_data = re.match(r"^(\d{2}/\d{2}/\d{4})\s+(.*)", linha)
            if not m_data:
                continue

            data = m_data.group(1)[:5]
            resto = m_data.group(2).strip()

            detalhes = []
            while i < len(linhas):
                prox = linhas[i].strip()
                if not prox:
                    i += 1
                    continue
                if re.match(r"^\d{2}/\d{2}/\d{4}\s", prox) or re.match(r"^\d{2}/\d{2}/\d{4}$", prox):
                    break
                if self.VALOR_M2_RE.search(prox):
                    break
                if self.IGNORAR_RE.search(prox):
                    i += 1
                    continue
                m_det = re.match(r"^\d{2}/\d{2}\s+\d{2}:\d{2}\s*(.*)", prox)
                detalhes.append(m_det.group(1) if m_det and m_det.group(1) else prox)
                i += 1

            m_val = self.VALOR_M2_RE.search(resto)
            if not m_val:
                continue

            valor_str = m_val.group(1)
            indicador = m_val.group(2)
            historico = resto[:m_val.start()].strip()
            historico = re.sub(r"^(?:\d{3,5}\s+){1,3}", "", historico).strip()
            
            historico = re.sub(r"\s+\d{6,}\s*$", "", historico).strip()

            if detalhes:
                historico = historico + " - " + " ".join(detalhes).strip()

            if not historico or len(historico) < 3 or self.IGNORAR_RE.search(historico):
                continue

            try:
                valor = float(valor_str.replace(".", "").replace(",", "."))
                if indicador == "D":
                    valor = -valor
            except ValueError:
                continue

            resultado.append(LancamentoBase(data, historico, valor, self.conta_banco))

        return resultado