import pdfplumber
import re
import io
from typing import List

POPPLER_PATH = r"C:\Users\Raquel\ConverterExtratosBancarios\poppler\poppler-25.12.0\Library\bin"
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

CONTA_APLIC  = "11161"
CONTA_SICOOB = "11120"
CONTA_IRRF   = "21504"

IGNORAR = [
    "saldo anterior", "saldo bruto", "saldo disponivel", "saldo disponível",
    "resumo", "ouvidoria", "numero da aplicacao", "número da aplicação",
    "modalidade", "data da aplicacao", "data da aplicação",
    "data fim", "vencimento", "conta:", "periodo", "período",
    "data historico", "data histórico", "extrato", "plataforma",
    "sistema", "cooperativa", "coop", "sicoob", "ass forn",
    "historico", "histórico", "valor", "sisbr",
]


def _extrair_texto_ocr(conteudo: bytes) -> str:
    import pikepdf
    import pytesseract
    from pdf2image import convert_from_bytes
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    pdf_obj = pikepdf.open(io.BytesIO(conteudo))
    buf = io.BytesIO()
    pdf_obj.save(buf)
    buf.seek(0)
    pages = convert_from_bytes(buf.read(), poppler_path=POPPLER_PATH, dpi=200)
    return "\n".join(pytesseract.image_to_string(p) for p in pages)


def _classificar(historico: str, cd: str) -> dict:
    h = historico.upper().strip()
    # Normaliza OCR: APROPRIAGAO → APROPRIACÃO
    h_norm = h.replace("GACAO", "CAÇÃO").replace("GAGAO", "CAÇÃO").replace("GACO", "CAÇÃO")

    if "APROPRIAC" in h or "APROPRIAG" in h:
        return {
            "conta_debito": CONTA_APLIC,
            "conta_credito": CONTA_SICOOB,
            "classificacao": "Receita / Entrada",
            "descricao": "Vr. apropriação de CM conf. extrato",
            "requer_revisao": False,
        }
    if "IRRF" in h or "RETENC" in h or "RETENG" in h:
        return {
            "conta_debito": CONTA_IRRF,
            "conta_credito": CONTA_APLIC,
            "classificacao": "Impostos / Tributos",
            "descricao": "Vr. ref. retenção de IRRF conf. extrato",
            "requer_revisao": False,
        }
    if "RESGATE" in h:
        return {
            "conta_debito": CONTA_SICOOB,
            "conta_credito": CONTA_APLIC,
            "classificacao": "Resgate de Aplicação",
            "descricao": "Vr. ref. resgate de aplicação financeira conf. extrato",
            "requer_revisao": False,
        }
    if cd == "C":
        return {
            "conta_debito": CONTA_APLIC,
            "conta_credito": CONTA_SICOOB,
            "classificacao": "Receita / Entrada",
            "descricao": f"Vr. recebido de {historico.lower()} conf. extrato",
            "requer_revisao": False,
        }
    return {
        "conta_debito": CONTA_SICOOB,
        "conta_credito": CONTA_APLIC,
        "classificacao": "Pagamento / Saída",
        "descricao": f"Vr. ref. {historico.lower()} conf. extrato",
        "requer_revisao": True,
    }


class ParserSicoobAplic:
    def __init__(self, conta_banco: str = CONTA_APLIC):
        self.conta_banco = conta_banco

    def parse(self, conteudo: bytes) -> List[dict]:
        # Tenta extração normal
        with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
            texto_total = ""
            for page in pdf.pages:
                texto_total += (page.extract_text(x_tolerance=3, y_tolerance=3) or "") + "\n"

        # Se vazio usa OCR
        if not texto_total.strip():
            texto_total = _extrair_texto_ocr(conteudo)

        return self._processar(texto_total)

    def _processar(self, texto: str) -> List[dict]:
        linhas = [l.strip() for l in texto.splitlines() if l.strip()]

        # Separa as três colunas que o OCR retorna em blocos separados
        datas = []
        historicos = []
        valores = []

        DATA_RE  = re.compile(r"^\d{2}/\d{2}/\d{4}$")
        VALOR_RE = re.compile(r"^(\d{1,3}(?:\.\d{3})*,\d{2})([CD]?)$")

        for linha in linhas:
            linha_lower = linha.lower()

            # Ignora linhas de cabeçalho/rodapé
            if any(ign in linha_lower for ign in IGNORAR):
                continue

            if DATA_RE.match(linha):
                datas.append(linha)
            elif VALOR_RE.match(linha):
                m = VALOR_RE.match(linha)
                val_str = m.group(1)
                cd = m.group(2) if m.group(2) else "C"  # sem C/D assume crédito
                valores.append((val_str, cd))
            elif len(linha) > 3 and not re.match(r"^\d+[\.,]\d+$", linha):
                historicos.append(linha)

        # Remove saldos das listas
        historicos = [h for h in historicos if not re.search(r"saldo", h, re.IGNORECASE)]
        datas = datas[:len(historicos)]  # alinha tamanhos

        resultado = []
        for i, hist in enumerate(historicos):
            data = datas[i][:5] if i < len(datas) else "00/00"  # DD/MM
            val_str, cd = valores[i] if i < len(valores) else ("0,00", "C")

            try:
                valor = float(val_str.replace(".", "").replace(",", "."))
                if cd == "D":
                    valor = -valor
            except ValueError:
                continue

            classif = _classificar(hist, cd)

            resultado.append({
                "data": data,
                "descricao": classif["descricao"],
                "valor": abs(valor),
                "tipo": "Crédito" if cd == "C" else "Débito",
                "conta_debito": classif["conta_debito"],
                "conta_credito": classif["conta_credito"],
                "classificacao": classif["classificacao"],
                "requer_revisao": classif["requer_revisao"],
            })

        return resultado