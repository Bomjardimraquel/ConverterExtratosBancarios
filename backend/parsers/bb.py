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
    Indicador C/D explícito no final.
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
            historico = self._historico_modelo1(linhas, i)
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

    def _historico_modelo1(self, linhas: List[str], i_valor: int) -> str:
        """
        Tenta extrair o histórico para a linha de valor em posição i_valor.

        Ordem de busca:
        1. Linha anterior ao valor que seja histórico (não data sozinha, não número só)
        2. Parte textual da linha de data+histórico (padrão B)
        3. Texto da própria linha de valor (após lote/doc)
        """
        linha_val = linhas[i_valor].strip()

        # Candidatos: i-1 e i-2
        for delta in [1, 2]:
            idx = i_valor - delta
            if idx < 0:
                continue
            cand = linhas[idx].strip()
            if not cand or self.IGNORAR_RE.search(cand):
                continue
            # Se for só data → não é histórico
            if re.match(r"^\d{2}/\d{2}/\d{4}\s*$", cand):
                continue
            # Se for "DD/MM/AAAA Histórico" → extrai histórico
            m = re.match(r"^\d{2}/\d{2}/\d{4}\s+(.+)", cand)
            if m:
                return m.group(1).strip()
            # Se for linha de só números/lote → pula
            if re.match(r"^[\d\s\./\-]+$", cand):
                continue
            # Linha de histórico puro
            return cand

        # Fallback: texto na linha do valor após lote/doc/cnpj
        texto = linha_val[:self.VALOR_M1_RE.search(linha_val).start()].strip()
        # Remove lote (4-5 dígitos) e doc numérico do início
        texto = re.sub(r"^(?:\d{4,6}\s+){1,3}", "", texto).strip()
        # Remove CNPJ
        texto = re.sub(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", "", texto).strip()
        return texto if len(texto) > 3 else ""

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

            # Pula linha de detalhe (DD/MM HH:MM ...)
            while i < len(linhas):
                prox = linhas[i].strip()
                if re.match(r"^\d{2}/\d{2}/\d{4}", prox):
                    break
                if re.match(r"^\d{2}/\d{2}\s+\d{2}:\d{2}", prox):
                    i += 1
                    continue
                break

            m_val = self.VALOR_M2_RE.search(resto)
            if not m_val:
                continue

            valor_str = m_val.group(1)
            indicador = m_val.group(2)
            historico = resto[:m_val.start()].strip()
            # Remove colunas numéricas do início (0000, 14024, 821)
            historico = re.sub(r"^(?:\d{3,5}\s+){1,3}", "", historico).strip()
            # Remove documento numérico longo do final
            historico = re.sub(r"\s+\d{6,}\s*$", "", historico).strip()

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
