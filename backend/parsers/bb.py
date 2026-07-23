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