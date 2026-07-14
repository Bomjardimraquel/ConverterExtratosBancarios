import pdfplumber
import re
import io
from parsers.base import ParserBase, LancamentoBase
from typing import List


class ParserBB(ParserBase):
    """
    Banco do Brasil — dois modelos reais.

    ── MODELO 1 (extrato PDF agência) ──────────────────────────────────────
    Padrão de cada lançamento (3 linhas, ordem variável):

    Padrão A:
      [linha i-1] "Histórico aqui"           ← descrição ANTES
      [linha i  ] "DD/MM/AAAA"               ← só a data
      [linha i+1] "lote doc [cnpj] valor(+/-)"

    Padrão B:
      [linha i  ] "DD/MM/AAAA Histórico aqui"  ← data + descrição juntos
      [linha i+1] "lote doc valor(+/-)"

    A linha com valor sempre termina com: "1.234,56 (+)" ou "344,54 (-)"
    Histórico NUNCA está na mesma linha que o valor (exceto quando
    não há lote/doc, ex: "9903 1.784,87 (-)")

    ── MODELO 2 (autoatendimento web) ──────────────────────────────────────
    "DD/MM/AAAA  0000  14024  732 Cielo Vendas Crédito  57.081.504  9.056,75 C  26.838,44 C"
    Indicador C/D explícito no final. Cada lançamento vem seguido de uma ou
    mais linhas de detalhe ("DD/MM HH:MM texto") com o favorecido/pagador —
    ESSENCIAL de preservar (nome de fornecedor, nome de quem pagou o PIX
    etc.), não é só ruído.
    """

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

    def parse(self, conteudo: bytes) -> List[LancamentoBase]:
        with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
            texto_total = "\n".join(
                p.extract_text(x_tolerance=3, y_tolerance=3) or "" for p in pdf.pages
            )
        if re.search(r"\d{1,3}(?:\.\d{3})*,\d{2}\s+[CD]\b", texto_total):
            return self._parse_modelo2(texto_total.splitlines())
        else:
            return self._parse_modelo1(texto_total.splitlines())

    # ─────────────────────────────────────────────────────────────────────────
    # MODELO 1
    # ─────────────────────────────────────────────────────────────────────────
    def _parse_modelo1(self, linhas: List[str]) -> List[LancamentoBase]:
        resultado = []
        n = len(linhas)
        # Linhas já usadas como detalhe-depois-do-valor de um lançamento
        # anterior — sem isso, essa mesma linha podia ser reaproveitada
        # (errado) como se fosse o RÓTULO do lançamento seguinte. Foi
        # assim que "20/04 16:35 CEF MATRIZ" (detalhe do Pix - Enviado de
        # R$382,40) acabou virando rótulo do "Cap Giro Dig Amortização"
        # de R$5.238,79 logo depois — dois lançamentos diferentes
        # misturados num só.
        linhas_consumidas: set = set()

        for i, linha in enumerate(linhas):
            linha = linha.strip()

            # Linha com valor(+/-) no final
            m_val = self.VALOR_M1_RE.search(linha)
            if not m_val:
                continue

            valor_str = m_val.group(1)
            sinal = m_val.group(2)

            # Ignora saldo do dia / saldo anterior
            if re.search(r"saldo", linha, re.IGNORECASE):
                continue

            # ── Extrai data ──────────────────────────────────────────────
            data = None
            # Tenta linha anterior (padrão A: data sozinha na linha i-1)
            if i >= 1:
                prev = linhas[i - 1].strip()
                m_d = re.match(r"^(\d{2}/\d{2}/\d{4})\s*$", prev)
                if m_d:
                    data = m_d.group(1)[:5]

            # Tenta 2 linhas antes (padrão A: histórico na i-2, data na i-1)
            if data is None and i >= 2:
                prev2 = linhas[i - 2].strip()
                m_d = re.match(r"^(\d{2}/\d{2}/\d{4})\s*$", prev2)
                if m_d:
                    data = m_d.group(1)[:5]

            # Tenta linha anterior como "DD/MM/AAAA Histórico" (padrão B)
            if data is None and i >= 1:
                prev = linhas[i - 1].strip()
                m_d = re.match(r"^(\d{2}/\d{2}/\d{4})\s+.+", prev)
                if m_d:
                    data = m_d.group(1)[:5]

            if data is None:
                continue

            # ── Extrai histórico ─────────────────────────────────────────
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
        """
        Extrai o histórico para a linha de valor em posição i_valor.

        ANTES: parava assim que achava QUALQUER candidato de histórico (o
        rótulo genérico "Pix - Recebido", "Cheque Compensado" etc na linha
        i-1/i-2) e nunca olhava pro detalhe de verdade (nome de quem pagou,
        CNPJ, número do documento), que em boa parte dos extratos reais do
        BB vem colado na PRÓPRIA linha do valor (padrão A: "lote doc
        DD/MM HH:MM cnpj NOME - valor(+/-)") ou numa linha DEPOIS dela
        (padrão B: "Cobrança referente...", "Número: 852745", "Rende
        Facil" etc). Resultado: raw saía só "Pix - Recebido", sem o nome
        do fornecedor/pagador — exatamente o dado que o Módulo 2 usa pra
        casar título/despesa.

        AGORA: monta "rótulo - detalhe", buscando o detalhe tanto na
        própria linha do valor quanto (se ela não tiver nada) na linha
        seguinte.
        """
        linha_val = linhas[i_valor].strip()
        m_val_local = self.VALOR_M1_RE.search(linha_val)
        texto_antes_valor = linha_val[:m_val_local.start()].strip()

        # Detalhe embutido na própria linha do valor (padrão A): tira lote
        # e documento (tokens numéricos/com ponto do início) e o que
        # sobrar — se não for só número/lixo — é o detalhe de verdade
        # (data/hora, CNPJ/CPF, nome).
        detalhe_embutido = re.sub(r"^(?:[\d.]{4,}\s+){0,3}", "", texto_antes_valor).strip()
        detalhe_embutido = re.sub(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", "", detalhe_embutido).strip()
        if re.match(r"^[\d\s./\-]*$", detalhe_embutido):
            detalhe_embutido = ""

        # Candidatos de rótulo: i-1 e i-2
        rotulo = None
        for delta in [1, 2]:
            idx = i_valor - delta
            if idx < 0:
                continue
            cand = linhas[idx].strip()
            if not cand or self.IGNORAR_RE.search(cand):
                continue
            # já é linha de valor de OUTRO lançamento — não é rótulo daqui
            if self.VALOR_M1_RE.search(cand):
                continue
            # já foi usada como detalhe-depois-do-valor de outro lançamento
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
            # Não achou rótulo nas linhas anteriores — usa o que sobrou
            # da própria linha do valor (fallback antigo).
            rotulo = detalhe_embutido or texto_antes_valor
            detalhe_embutido = ""

        historico = rotulo
        if detalhe_embutido:
            historico = f"{historico} - {detalhe_embutido}"
        elif i_valor + 1 < len(linhas):
            # Padrão B: detalhe (nome do fornecedor, "Cobrança referente",
            # "Número: ...") vem numa linha DEPOIS da linha do valor.
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

    # ─────────────────────────────────────────────────────────────────────────
    # MODELO 2
    # ─────────────────────────────────────────────────────────────────────────
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

            # Captura a(s) linha(s) de detalhe até o próximo lançamento.
            # ANTES: só capturava linha no formato "DD/MM HH:MM texto"
            # (detalhe de PIX/compra com cartão) — parava na primeira
            # linha que não batesse com esse formato. Nome de fornecedor
            # de BOLETO ("VIACAO AGUIA BRANCA S A", "MULTIPLIKE
            # SECURITIZADORA S.A." etc) vem em linha solta, sem prefixo de
            # data/hora nenhum, e por isso nunca era capturado — sumia
            # 100% dos boletos (86 de 86 na validação com a Diniz).
            # AGORA: captura qualquer linha até o próximo lançamento ou
            # valor, só tirando o prefixo "DD/MM HH:MM" quando existir
            # (pra não repetir a data, que já está na coluna própria).
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
            # Remove colunas numéricas do início (0000, 14024, 821)
            historico = re.sub(r"^(?:\d{3,5}\s+){1,3}", "", historico).strip()
            # Remove documento numérico longo do final (dígito corrido —
            # documentos com ponto, ex. 811.874.307.105.044, passam batido;
            # não atrapalha o Módulo 2 porque a extração de nome/CPF já
            # limpa esses padrões separadamente)
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