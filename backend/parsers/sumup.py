import pdfplumber
import re
import io
from parsers.base import ParserBase, LancamentoBase
from typing import List


class ParserSumUp(ParserBase):
    """
    SumUp Bank — "Extrato bancário por período".

    Layout em tabela, uma linha por lançamento:
      "DD/MM/AAAA HH:MM  Valor  Tipo  Descrição"

    Onde:
      - Valor vem SEM sinal quando é crédito ("76,24") e com um "-"
        (com espaço antes do número: "- 3.200,00") quando é débito.
        Não há indicador C/D — o sinal em si já diz a direção.
      - "Tipo" é uma das colunas fixas observadas no extrato real
        (Vendas SumUp, Pix recebido, Pix enviado, Pagamento de conta).
        Vendas SumUp nunca tem descrição (fica em branco); os outros
        tipos trazem o nome do favorecido/pagador logo depois, que o
        pdfplumber pode quebrar em 1-3 linhas seguintes quando o nome é
        comprido (ex.: "HIPERCG COMERCIO E" / "IMPORTACAO DE PECAS" /
        "LTDA").
    """

    IGNORAR_RE = re.compile(
        r"extrato banc|documento gerado|nome do correntista|cnpj|"
        r"dados da conta|saldo em|data e hora|ainda com d|fale com a gente|"
        r"ouvidoria|custo de liga|atendimento de segunda|^\s*$",
        re.IGNORECASE
    )

    # Início de uma linha de lançamento: "DD/MM/AAAA HH:MM "
    DATA_RE = re.compile(r"^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}\s+")

    # Tipos conhecidos, confirmados contra extrato real (ver docstring).
    # Se o SumUp introduzir um tipo novo não listado aqui, a linha some
    # silenciosamente — por isso, ao integrar um extrato novo, sempre
    # validar a soma total contra a variação de saldo (ver README do
    # projeto) pra pegar isso.
    TIPOS = "Vendas SumUp|Pix recebido|Pix enviado|Pagamento de conta"

    LINHA_RE = re.compile(
        r"^(\d{2}/\d{2}/\d{4})\s+\d{2}:\d{2}\s+"
        r"(-)?\s?(\d{1,3}(?:\.\d{3})*,\d{2})\s+"
        r"(" + TIPOS + r")"
        r"\s*(.*)$"
    )

    def parse(self, conteudo: bytes) -> List[LancamentoBase]:
        resultado = []
        with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
            texto_total = ""
            for page in pdf.pages:
                texto_total += (page.extract_text(x_tolerance=3, y_tolerance=3) or "") + "\n"

        linhas = texto_total.splitlines()
        n = len(linhas)
        i = 0

        while i < n:
            linha = linhas[i].strip()
            i += 1

            if not linha or self.IGNORAR_RE.search(linha):
                continue

            m = self.LINHA_RE.match(linha)
            if not m:
                continue

            data_str, sinal, valor_str, tipo, resto = m.groups()
            data = data_str[:5]  # DD/MM, sem ano

            # ── Coleta continuação da descrição (nome quebrado em várias
            # linhas) até o próximo lançamento ou fim da tabela ──────────
            detalhe = [resto] if resto else []
            while i < n:
                prox = linhas[i].strip()
                if not prox or self.DATA_RE.match(prox) or self.IGNORAR_RE.search(prox):
                    break
                detalhe.append(prox)
                i += 1

            descricao_extra = " ".join(p for p in detalhe if p).strip()
            historico = f"{tipo} - {descricao_extra}" if descricao_extra else tipo

            try:
                valor = float(valor_str.replace(".", "").replace(",", "."))
            except ValueError:
                continue
            if sinal == "-":
                valor = -valor

            resultado.append(LancamentoBase(data, historico, valor, self.conta_banco))

        return resultado