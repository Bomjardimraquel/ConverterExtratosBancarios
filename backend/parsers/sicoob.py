import pdfplumber
import re
import io
from parsers.base import ParserBase, LancamentoBase
from typing import List

POPPLER_PATH = r"C:\Users\Raquel\ConverterExtratosBancarios\poppler\poppler-25.12.0\Library\bin"
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def _extrair_texto_ocr(conteudo: bytes) -> str:
    """Remove proteção com pikepdf e extrai texto via OCR."""
    import pikepdf
    import pytesseract
    from pdf2image import convert_from_bytes

    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

    pdf_obj = pikepdf.open(io.BytesIO(conteudo))
    buf = io.BytesIO()
    pdf_obj.save(buf)
    buf.seek(0)

    pages = convert_from_bytes(buf.read(), poppler_path=POPPLER_PATH, dpi=200)
    texto_total = ""
    for page in pages:
        texto_total += pytesseract.image_to_string(page) + "\n"
    return texto_total


class ParserSicoob(ParserBase):
    """
    Sicoob — dois modelos reais:

    MODELO 1 (autopecas / SISBR compacto):
      Linha única por lançamento: "DD/MM HISTÓRICO ValorC"
      Ex:
        27/02 PIX RECEB.OUTRA IF 140,00C
        27/02 CR CP CR OT BAND 44,88C
        25/02 PGS-CH PRÓP COOP/AG 6.224,43D

    MODELO 2 (botelho / SISBR completo com documento):
      Colunas: Data | Documento | Histórico (multilinhas) | Valor
      Valor tem prefixo "R$" e sufixo C/D
      Ex:
        02/02  8288963  TRANSF.RECEBIDA - PIX SICOOB     R$ 15,00C
                        REM.: RONALDO SANTOS ALVARENGA
        02/02  IOF/2-2  DÉB.IOF                          R$ 16,51D
        03/02  129      DÉBITO PACOTE SERVIÇOS            R$ 44,00D
    """

    IGNORAR_RE = re.compile(
        r"saldo\s*(do\s*dia|anterior|bloq|disponível)|resumo|"
        r"encargos|informações|sac:|ouvidoria|cooperativa|conta:|período|"
        r"custo efetivo|taxa cheque|vencimento|^\s*$|"
        r"histórico de movimentação|data\s+documento|"
        r"extrato conta corrente|plataforma de serviços|"
        r"sistema de cooperativas",
        re.IGNORECASE
    )

    VALOR_RE = re.compile(r"R?\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2})([CD])\s*$")

    def parse(self, conteudo: bytes) -> List[LancamentoBase]:
        # Tenta extração normal com pdfplumber
        with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
            texto_total = ""
            for page in pdf.pages:
                texto_total += (page.extract_text(x_tolerance=3, y_tolerance=3) or "") + "\n"

        # Se vazio, usa OCR
        if not texto_total.strip():
            texto_total = _extrair_texto_ocr(conteudo)

        # Detecta modelo 2 pela presença de "R$" nos valores
        if "R$" in texto_total:
            return self._parse_modelo2(texto_total)
        else:
            return self._parse_modelo1(texto_total)

    # ─────────────────────────────────────────────────────────────────────────
    # MODELO 1 — linha única por lançamento
    # ─────────────────────────────────────────────────────────────────────────
    def _parse_modelo1(self, texto: str) -> List[LancamentoBase]:
        resultado = []
        linhas = texto.splitlines()
        i = 0
        while i < len(linhas):
            linha = linhas[i].strip()
            i += 1

            if self.IGNORAR_RE.search(linha):
                continue

            m = re.match(r"^(\d{2}/\d{2})\s+(.+?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})([CD])\s*$", linha)
            if not m:
                continue

            data, historico, valor_str, indicador = m.groups()
            historico = historico.strip()

            if i < len(linhas):
                prox = linhas[i].strip()
                if prox and not re.match(r"^\d{2}/\d{2}\s", prox) and not self.VALOR_RE.search(prox):
                    if not self.IGNORAR_RE.search(prox):
                        historico = historico + " - " + prox
                    i += 1
                    while i < len(linhas):
                        extra = linhas[i].strip()
                        if re.match(r"^\*{3}\.\d{3}|\bDOC\.:", extra) or re.match(r"^[A-Z]{2,}", extra) and len(extra) < 30:
                            i += 1
                        else:
                            break

            try:
                valor = float(valor_str.replace(".", "").replace(",", "."))
                if indicador == "D":
                    valor = -valor
            except ValueError:
                continue

            resultado.append(LancamentoBase(data, historico, valor, self.conta_banco))

        return resultado

    # ─────────────────────────────────────────────────────────────────────────
    # MODELO 2 — com documento e valor prefixado por R$
    # ─────────────────────────────────────────────────────────────────────────
    def _parse_modelo2(self, texto: str) -> List[LancamentoBase]:
        resultado = []
        linhas = texto.splitlines()
        i = 0

        while i < len(linhas):
            linha = linhas[i].strip()
            i += 1

            if self.IGNORAR_RE.search(linha):
                continue

            m = re.match(r"^(\d{2}/\d{2})\s+", linha)
            if not m:
                continue

            data = m.group(1)
            resto = linha[m.end():].strip()
            resto = re.sub(r"^[\w/\-\.]+\s+", "", resto, count=1)

            m_val = self.VALOR_RE.search(linha)
            if not m_val:
                if i < len(linhas) and self.VALOR_RE.search(linhas[i].strip()):
                    m_val = self.VALOR_RE.search(linhas[i].strip())
                    i += 1
                else:
                    continue

            valor_str = m_val.group(1)
            indicador = m_val.group(2)

            historico = re.sub(r"\s*R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}[CD]\s*$", "", resto).strip()
            historico = re.sub(r"^R\$\s*", "", historico).strip()

            detalhes = []
            while i < len(linhas):
                prox = linhas[i].strip()
                if not prox or re.match(r"^\d{2}/\d{2}\s", prox) or self.IGNORAR_RE.search(prox):
                    break
                if self.VALOR_RE.search(prox):
                    break
                if re.match(r"^(REM\.|FAV\.|Transferência|Recebimento|Pagamento|\*{3}\.)", prox):
                    if not re.match(r"^\*{3}\.|\bDOC\.", prox):
                        detalhes.append(prox)
                    i += 1
                else:
                    break

            if detalhes:
                detalhe_txt = detalhes[0].replace("REM.:", "").replace("FAV.:", "").strip()
                if len(detalhe_txt) > 3:
                    historico = historico + " - " + detalhe_txt

            if not historico or len(historico) < 3:
                continue
            if self.IGNORAR_RE.search(historico):
                continue

            try:
                valor = float(valor_str.replace(".", "").replace(",", "."))
                if indicador == "D":
                    valor = -valor
            except ValueError:
                continue

            resultado.append(LancamentoBase(data, historico, valor, self.conta_banco))

        return resultado
