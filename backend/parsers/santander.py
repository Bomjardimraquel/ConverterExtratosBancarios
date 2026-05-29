import pdfplumber
import re
import io
from parsers.base import ParserBase, LancamentoBase
from typing import List


class ParserSantander(ParserBase):
    """
    Santander Empresas.

    O pdfplumber extrai 3 faixas de y por lançamento:
      y-7 → hist linha 1  (col hist, sem data nem valor)
      y   → data + valor  (col data e valor)
      y+7 → hist linha 2  (col hist — complemento)

    Estratégia: percorre as linhas físicas (janela y=3pt).
    Quando encontra uma linha com DATA+VALOR:
      - hist = linha anterior imediata (se existir, sem data/valor) + hist inline + próxima linha imediata (se sem data/valor)
    """

    IGNORAR_RE = re.compile(
        r"aplicativo santander|r\s*b\s*comercio|agência|conta:|períodos:|"
        r"data/hora|saldo disponível|posição\s*em|entenda a composição|"
        r"[a-j]\s*[–-]\s*saldo|central de atendimento|4004-|0800\s|"
        r"sac\s*-|ouvidoria|deficiência|desbloqueio|provisão|limite cheque|"
        r"^\s*$|^\d+/\d+$|valor\s*\(r\$\)|juros acumulados|iof acumulado",
        re.IGNORECASE
    )

    VALOR_RE = re.compile(r"^-?\d{1,3}(?:\.\d{3})*,\d{2}$")
    DATA_RE  = re.compile(r"^\d{2}/\d{2}/\d{4}$")
    X_DATA   = (20,  75)
    X_HIST   = (76, 390)
    X_VALOR  = (391, 510)
    # Saldo: x > 510 — ignorado

    def parse(self, conteudo: bytes) -> List[LancamentoBase]:
        resultado = []
        with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
            for page in pdf.pages:
                resultado += self._parse_page(page)
        return resultado

    def _col(self, x):
        if self.X_DATA[0]  <= x <= self.X_DATA[1]:  return 'data'
        if self.X_HIST[0]  <= x <= self.X_HIST[1]:  return 'hist'
        if self.X_VALOR[0] <= x <= self.X_VALOR[1]: return 'valor'
        return 'saldo'

    def _parse_page(self, page) -> List[LancamentoBase]:
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        if not words:
            return []

        # Agrupa por y (janela 3pt)
        lfs = []
        for w in words:
            y = (w['top'] + w['bottom']) / 2
            for lf in lfs:
                if abs(lf[0] - y) < 3:
                    lf[1].append(w); break
            else:
                lfs.append([y, [w]])
        lfs.sort(key=lambda lf: lf[0])

        # Converte para rows: (y, data, hist, valor)
        rows = []
        for y, ws in lfs:
            d, h, v = [], [], []
            for w in ws:
                c = self._col(w['x0'])
                if c == 'data':   d.append(w['text'])
                elif c == 'hist': h.append(w['text'])
                elif c == 'valor': v.append(w['text'])
            rows.append((y, ' '.join(d).strip(), ' '.join(h).strip(), ' '.join(v).strip()))

        n = len(rows)
        resultado = []
        usadas = set()

        for i, (y0, data, hist, valor) in enumerate(rows):
            if not self.DATA_RE.match(data):
                continue
            if i in usadas:
                continue

            usadas.add(i)

            # Remove documento do hist inline
            hist = re.sub(r'\b\d{6,10}\b', '', hist).strip()

            # Linha ANTES (hist acima): se existir, não tiver data nem valor,
            # e estiver dentro de 15pt de y0
            hist_antes = ''
            if i > 0 and (i-1) not in usadas:
                yp, dp, hp, vp = rows[i-1]
                if abs(yp - y0) <= 15 and not self.DATA_RE.match(dp) and not vp:
                    hist_antes = hp
                    usadas.add(i-1)

            # Linha DEPOIS (hist abaixo): mesma lógica
            hist_depois = ''
            if i + 1 < n and (i+1) not in usadas:
                yn, dn, hn, vn = rows[i+1]
                if abs(yn - y0) <= 15 and not self.DATA_RE.match(dn) and not vn:
                    hist_depois = hn
                    usadas.add(i+1)

            historico = ' '.join(filter(None, [hist_antes, hist, hist_depois])).strip()
            historico = re.sub(r'\s{2,}', ' ', historico)[:100]

            valor_txt = valor
            if not valor_txt:
                # Às vezes o valor está no campo hist (caso raro)
                mv = re.search(r'-?\d{1,3}(?:\.\d{3})*,\d{2}', historico)
                if mv:
                    valor_txt = mv.group()
                    historico = (historico[:mv.start()] + historico[mv.end():]).strip()

            if not historico or len(historico) < 3:
                continue
            if self.IGNORAR_RE.search(historico):
                continue
            if not valor_txt or not self.VALOR_RE.match(valor_txt):
                continue

            try:
                valor_f = float(valor_txt.replace('.', '').replace(',', '.'))
            except ValueError:
                continue

            resultado.append(LancamentoBase(data[:5], historico, valor_f, self.conta_banco))

        return resultado