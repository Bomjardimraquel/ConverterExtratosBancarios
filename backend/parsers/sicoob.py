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

    MODELO 1 (SISBR compacto):
      O pdfplumber pode quebrar valor e/ou indicador em linhas separadas.
      Casos possíveis para um mesmo lançamento:

        Caso 1 — tudo junto:        "DD/MM HIST 1.234,56C"
        Caso 2 — indicador separado:"DD/MM HIST 1.234,56"  → "C"
        Caso 3 — valor antes:       "1.234,56"  → "DD/MM HIST"  → "C"
        Caso 4 — valor+ind sep.:    "DD/MM HIST" → "1.234,56"   → "C"

    MODELO 2 (SISBR completo com documento):
      Colunas: Data | Documento | Histórico | Valor com R$ e C/D
    """

    IGNORAR_RE = re.compile(
        r"saldo\s*(do\s*dia|anterior|bloq|disponível)|resumo|"
        r"encargos|informações|sac:|ouvidoria|cooperativa:|conta:|período|"
        r"custo efetivo|taxa cheque|vencimento|^\s*$|"
        r"histórico de movimentação|data\s+documento|"
        r"extrato conta corrente|plataforma de serviços|"
        r"sistema de cooperativas|"
        r"https?://|sicoob\s*\|\s*internet banking|"
        r"^\d{2}/\d{2}/\d{4},?\s*\d{2}:\d{2}",  # cabeçalho de página repetido ("10/06/2026, 10:03 ...")
        re.IGNORECASE
    )

    # Valor + indicador colados no final da linha
    VALOR_CD_RE  = re.compile(r"(\d{1,3}(?:\.\d{3})*,\d{2})([CD])\s*$")
    # Só o número, sem indicador
    NUMERO_RE    = re.compile(r"^\s*(\d{1,3}(?:\.\d{3})*,\d{2})\s*$")
    # Só o indicador
    INDICADOR_RE = re.compile(r"^\s*([CD])\s*$")
    # Início de linha de lançamento
    DATA_RE      = re.compile(r"^\d{2}/\d{2}\s")

    # Linhas de "lixo" que aparecem dentro do bloco de um lançamento e não
    # carregam informação nenhuma (só rótulo). REM.:/FAV.: NÃO entram aqui
    # de propósito: essas linhas trazem o nome de quem recebeu/remeteu a
    # transferência (ex: "FAV.: AREUDO BARBOSA GUIMARAES") — descartar a
    # linha inteira jogava fora justamente o nome, e nos casos em que o
    # nome não se repetia em nenhuma linha depois, o detalhe acabava
    # pegando por engano o nome da PRÓPRIA empresa (que aparece depois,
    # como parte do identificador da operação) em vez do favorecido real.
    # Ver REM_FAV_RE abaixo: a linha é mantida, só o rótulo é cortado.
    LIXO_RE = re.compile(
        r"^(DOC\.:|SIPAG_|NOME:|CPF CNPJ:|"
        r"Recebimento Pix|Pagamento Pix|Transferência Pix)",
        re.IGNORECASE
    )
    # REM.: / FAV.: — mantém a linha, corta só o rótulo
    REM_FAV_RE = re.compile(r"^(?:REM\.:|FAV\.:)\s*", re.IGNORECASE)
    CPFCNPJ_RE = re.compile(
        r"^[\*\d]{3}\.[\*\d]{3}\.[\*\d]{3}|^\d{2}\.\d{3}\.\d{3}"
    )

    def parse(self, conteudo: bytes) -> List[LancamentoBase]:
        with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
            texto_total = ""
            for page in pdf.pages:
                texto_total += (page.extract_text(x_tolerance=3, y_tolerance=3) or "") + "\n"

        if not texto_total.strip():
            texto_total = _extrair_texto_ocr(conteudo)

        if "R$" in texto_total:
            return self._parse_modelo2(texto_total)
        else:
            return self._parse_modelo1(texto_total)

    # ─────────────────────────────────────────────────────────────────────────
    # MODELO 1
    # ─────────────────────────────────────────────────────────────────────────
    def _parse_modelo1(self, texto: str) -> List[LancamentoBase]:
        resultado = []
        linhas = texto.splitlines()
        n = len(linhas)

        # Pré-processamento: número solto na linha ANTES de um DD/MM
        # (pdfplumber joga o valor da coluna direita acima do histórico)
        valor_antes = {}  # idx da linha DD/MM → valor_str
        for idx in range(n - 1):
            l = linhas[idx].strip()
            mn = self.NUMERO_RE.match(l)
            if mn:
                prox = linhas[idx + 1].strip() if idx + 1 < n else ""
                if self.DATA_RE.match(prox):
                    valor_antes[idx + 1] = mn.group(1)

        i = 0
        while i < n:
            linha = linhas[i].strip()
            idx_linha = i
            i += 1

            if not linha or self.IGNORAR_RE.search(linha):
                continue

            # ── Extrai data + histórico + valor + indicador ──────────────────
            data = None
            historico = None
            valor_str = None
            indicador = None

            # Caso 1: "DD/MM HIST ValorC" tudo na mesma linha
            m1 = re.match(
                r"^(\d{2}/\d{2})\s+(.+?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})([CD])\s*$",
                linha
            )
            if m1:
                data, historico, valor_str, indicador = m1.groups()

            else:
                # Exige DD/MM + algum texto
                m0 = re.match(r"^(\d{2}/\d{2})\s+(.+?)$", linha)
                if not m0:
                    continue
                data = m0.group(1)
                raw_hist = m0.group(2).strip()

                # Verifica se o histórico já termina com número (Caso 2)
                m_num_fim = re.search(r"\s+(\d{1,3}(?:\.\d{3})*,\d{2})$", raw_hist)
                if m_num_fim:
                    # Número no fim do histórico → indicador deve estar na próxima
                    possivel_valor = m_num_fim.group(1)
                    historico = raw_hist[: m_num_fim.start()].strip()
                    j = i
                    while j < n and not linhas[j].strip():
                        j += 1
                    if j < n:
                        mi = self.INDICADOR_RE.match(linhas[j].strip())
                        if mi:
                            valor_str = possivel_valor
                            indicador = mi.group(1)
                            i = j + 1
                    if not valor_str:
                        continue
                else:
                    historico = raw_hist

                    # Caso 3: valor estava na linha ANTERIOR
                    if idx_linha in valor_antes:
                        valor_str = valor_antes[idx_linha]
                        j = i
                        while j < n and not linhas[j].strip():
                            j += 1
                        if j < n:
                            mi = self.INDICADOR_RE.match(linhas[j].strip())
                            if mi:
                                indicador = mi.group(1)
                                i = j + 1
                        if not indicador:
                            continue

                    else:
                        # Caso 4: valor e indicador nas linhas seguintes
                        j = i
                        tentativas = 0
                        while j < n and tentativas < 6:
                            prox = linhas[j].strip()
                            if not prox:
                                j += 1; tentativas += 1; continue

                            # Valor+indicador juntos
                            mv = self.VALOR_CD_RE.search(prox)
                            if mv and re.match(r"^\d", prox):
                                valor_str = mv.group(1)
                                indicador = mv.group(2)
                                i = j + 1
                                break

                            # Número solto + indicador na linha depois
                            mn = self.NUMERO_RE.match(prox)
                            if mn and j + 1 < n:
                                mi = self.INDICADOR_RE.match(linhas[j + 1].strip())
                                if mi:
                                    valor_str = mn.group(1)
                                    indicador = mi.group(1)
                                    i = j + 2
                                    break

                            # Indicador solto → para
                            if self.INDICADOR_RE.match(prox):
                                break

                            # Lixo → pula
                            if (self.LIXO_RE.match(prox)
                                    or self.CPFCNPJ_RE.match(prox)
                                    or re.match(r"^\d{2}\.\d{3}\.\d{3}", prox)):
                                j += 1; tentativas += 1; continue

                            # Próximo lançamento → para
                            if self.DATA_RE.match(prox):
                                break

                            break  # texto desconhecido

                        if not valor_str or not indicador:
                            continue

            if not data or not historico or not valor_str or not indicador:
                continue

            # ── Coleta detalhe descritivo até o próximo lançamento ───────────
            detalhe = None
            while i < n:
                prox = linhas[i].strip()
                if not prox:
                    i += 1; continue
                if self.DATA_RE.match(prox):
                    break
                if self.IGNORAR_RE.search(prox):
                    i += 1; continue
                if self.VALOR_CD_RE.search(prox) and re.match(r"^\d", prox):
                    i += 1; continue
                if self.NUMERO_RE.match(prox) or self.INDICADOR_RE.match(prox):
                    i += 1; continue
                if (self.LIXO_RE.match(prox)
                        or self.CPFCNPJ_RE.match(prox)
                        or re.match(r"^\d{2}\.\d{3}\.\d{3}", prox)):
                    i += 1; continue
                m_rf = self.REM_FAV_RE.match(prox)
                if m_rf:
                    prox = prox[m_rf.end():].strip()
                    if not prox:
                        i += 1; continue
                if detalhe is None:
                    detalhe = prox
                i += 1

            if detalhe:
                historico = historico + " - " + detalhe

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
            # A coluna "Documento" normalmente é um token só (número,
            # "Pix", "MASTERCARD" etc) e por isso um strip de UM token já
            # bastava. Mas o código de aplicação/resgate automático de RDC
            # vem em mais de um token ("RDC AUT", "64 - 1") — e como
            # "RDC AUT" começa igual ao histórico "RDC AUTOMÁTICO" que vem
            # logo depois, sobrava um pedaço solto ("AUT RDC AUTOMÁTICO",
            # "- 1 RESGATE RDC AUTOMÁTICO") grudado no início do histórico.
            m_doc_multi = re.match(r"^(?:\d+\s*-\s*\d+|RDC\s+AUT)\s+", resto)
            if m_doc_multi:
                resto = resto[m_doc_multi.end():].strip()
            else:
                resto = re.sub(r"^[\w/\-\.]+\s+", "", resto, count=1)

            m_val = self.VALOR_CD_RE.search(linha)
            if not m_val:
                if i < len(linhas) and self.VALOR_CD_RE.search(linhas[i].strip()):
                    m_val = self.VALOR_CD_RE.search(linhas[i].strip())
                    i += 1
                else:
                    continue

            valor_str = m_val.group(1)
            indicador = m_val.group(2)

            historico = re.sub(
                r"\s*R?\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}[CD]\s*$", "", resto
            ).strip()
            historico = re.sub(r"^R\$\s*", "", historico).strip()

            # ANTES: só capturava a linha de detalhe se começasse com
            # REM./FAV./Transferência/Recebimento/Pagamento — detalhe de
            # boleto/título ("MAT ESCRITORIO", "MENSALIDADE UNIMED 05.2026")
            # é texto livre, não bate com nenhum desses prefixos, e sumia
            # sem nunca entrar no histórico.
            # AGORA: captura qualquer linha até o próximo lançamento/valor,
            # só pulando CPF/CNPJ mascarado solto e "DOC.:" (que não
            # agregam nome nenhum).
            detalhes = []
            while i < len(linhas):
                prox = linhas[i].strip()
                if not prox:
                    i += 1
                    continue
                if re.match(r"^\d{2}/\d{2}\s", prox) or self.IGNORAR_RE.search(prox):
                    break
                if self.VALOR_CD_RE.search(prox):
                    break
                if re.match(r"^\*{3}\.\d{3}\.\d{3}-\*{2}\s*$", prox) or re.match(r"^DOC\.:", prox, re.IGNORECASE):
                    i += 1
                    continue
                detalhes.append(prox)
                i += 1

            if detalhes:
                detalhe_txt = " ".join(detalhes)
                detalhe_txt = detalhe_txt.replace("REM.:", "").replace("FAV.:", "").strip()
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