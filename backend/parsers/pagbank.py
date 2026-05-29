import pdfplumber
import re
import io
from parsers.base import ParserBase, LancamentoBase
from typing import List


class ParserPagBank(ParserBase):
    """
    PagBank (PagSeguro) — formato simples, tudo na mesma linha:
      "DD/MM/AAAA Descrição R$ 1.234,56"
    Filtra linhas de saldo do dia.
    """

    IGNORAR_RE = re.compile(
        r"saldo\s*do\s*dia|saldo\s*anterior|extrato\s*da\s*conta|"
        r"emitido\s*em|periodo:|data\s+descri|agência|conta\s+\d|"
        r"cnpj:|pagseguro|r\s*b\s*comercio|^\s*$",
        re.IGNORECASE
    )

    LINHA_RE = re.compile(
        r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+R\$\s*([\d\.]+,\d{2})\s*$"
    )

    def parse(self, conteudo: bytes) -> List[LancamentoBase]:
        resultado = []
        with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
            for page in pdf.pages:
                texto = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                for linha in texto.splitlines():
                    linha = linha.strip()
                    if not linha or self.IGNORAR_RE.search(linha):
                        continue

                    m = self.LINHA_RE.match(linha)
                    if not m:
                        continue

                    data_str, historico, valor_str = m.groups()
                    data = data_str[:5]  # DD/MM
                    historico = historico.strip()

                    # PagBank só tem créditos no extrato (vendas e rendimentos)
                    try:
                        valor = float(valor_str.replace(".", "").replace(",", "."))
                    except ValueError:
                        continue

                    resultado.append(LancamentoBase(data, historico, valor, self.conta_banco))

        return resultado