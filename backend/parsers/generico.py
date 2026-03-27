import pdfplumber
import re
import io
from parsers.base import ParserBase, LancamentoBase
from typing import List


class ParserGenerico(ParserBase):
    """
    Parser genérico para bancos sem parser dedicado (Bradesco, Santander, PagBank, Nordeste).
    Tenta múltiplos padrões comuns de extratos bancários brasileiros.
    """

    IGNORAR_RE = re.compile(
        r"saldo|total|anterior|^\s*$|agência|conta|período|cliente|cnpj|cpf|"
        r"https?://|sac\s|ouvidoria|atualizado|banco\s",
        re.IGNORECASE
    )

    # Padrão 1: DD/MM/AAAA ... ValorC/D  (sufixo C ou D)
    RE_CD = re.compile(
        r"^(\d{2}/\d{2}(?:/\d{2,4})?)\s+(.+?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s*([CD])\s*$"
    )
    # Padrão 2: DD/MM/AAAA ... -Valor ou +Valor (sinal)
    RE_SINAL = re.compile(
        r"^(\d{2}/\d{2}(?:/\d{2,4})?)\s+(.+?)\s+([-+]?\d{1,3}(?:\.\d{3})*,\d{2})\s*$"
    )

    def parse(self, conteudo: bytes) -> List[LancamentoBase]:
        resultado = []
        with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
            for page in pdf.pages:
                texto = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                for linha in texto.splitlines():
                    linha = linha.strip()
                    if self.IGNORAR_RE.search(linha):
                        continue

                    # Tenta padrão C/D
                    m = self.RE_CD.match(linha)
                    if m:
                        data, historico, valor_str, indicador = m.groups()
                        try:
                            valor = float(valor_str.replace(".", "").replace(",", "."))
                            if indicador == "D":
                                valor = -valor
                            resultado.append(LancamentoBase(data[:5], historico.strip(), valor, self.conta_banco))
                        except ValueError:
                            pass
                        continue

                    # Tenta padrão com sinal
                    m = self.RE_SINAL.match(linha)
                    if m:
                        data, historico, valor_str = m.groups()
                        try:
                            valor = float(valor_str.replace(".", "").replace(",", "."))
                            resultado.append(LancamentoBase(data[:5], historico.strip(), valor, self.conta_banco))
                        except ValueError:
                            pass

        return resultado
