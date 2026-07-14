import pdfplumber
import re
import io
from parsers.base import ParserBase, LancamentoBase
from typing import List


class ParserItau(ParserBase):

    IGNORAR_DATA = re.compile(
        r"saldo\s*(total|anterior|disponível|bloq)|lançamentos do período|"
        r"atualizado em|em caso de dúvida|reclamações|ouvidoria|sac\s|"
        r"itau\.com\.br|deficiente|data\s+lançamentos|"
        r"razão social|cnpj.cpf|valor\s*\(r\$\)|saldo\s*\(r\$\)|"
        r"limite da conta|aviso:|^itaú|adeir material|agência|"
        r"lançamentos do período|saldo total|r\$ \d",
        re.IGNORECASE
    )

    VALOR_RE    = re.compile(r"^-?\d{1,3}(?:\.\d{3})*,\d{2}$")
    DATA_RE     = re.compile(r"^\d{2}/\d{2}/\d{4}$")
    CNPJ_CPF_RE = re.compile(r"^\d{2,3}\.\d{3}\.\d{3}[/\-]\d{4,6}[-]?\d{0,2}$")

    INICIO_LANC_RE = re.compile(
        r"^(RECEBIMENTO|RECEBIMENTOS|BOLETO|BOLETOS|PIX|RENDIMENTOS?|"
        r"PAGAMENTOS?|SALDO|TARIFA|D[ÉE]BITO|CR[ÉE]DITO|RESGATE|"
        r"APLICA[ÇC][ÃA]O|TRANSFER[ÊE]NCIA|CHEQUE)",
        re.IGNORECASE
    )

    X_DATA    = (20,  80)
    X_LANC    = (81, 220)
    X_RAZAO   = (221, 360)
    X_CNPJ    = (361, 460)
    X_VALOR   = (461, 570)

    def parse(self, conteudo: bytes) -> List[LancamentoBase]:
        
        linhas_cols_doc: List[tuple] = []
        with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
            for page in pdf.pages:
                linhas_cols_doc.extend(self._linhas_cols_da_pagina(page))
        return self._monta_lancamentos(linhas_cols_doc)

    def _linhas_cols_da_pagina(self, page) -> List[tuple]:
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        if not words:
            return []

        linhas_fisicas = [] 
        for w in words:
            y = (w['top'] + w['bottom']) / 2
            adicionado = False
            for lf in linhas_fisicas:
                if abs(lf[0] - y) < 8:
                    lf[1].append(w)
                    adicionado = True
                    break
            if not adicionado:
                linhas_fisicas.append([y, [w]])

        linhas_fisicas.sort(key=lambda lf: lf[0])

        def col(x):
            if self.X_DATA[0] <= x <= self.X_DATA[1]:    return 'data'
            if self.X_LANC[0] <= x <= self.X_LANC[1]:    return 'lanc'
            if self.X_RAZAO[0] <= x <= self.X_RAZAO[1]:  return 'razao'
            if self.X_CNPJ[0] <= x <= self.X_CNPJ[1]:   return 'cnpj'
            if self.X_VALOR[0] <= x <= self.X_VALOR[1]:  return 'valor'
            return 'outro'

        linhas_cols = []  # [(y, {col: texto})]
        for y, ws in linhas_fisicas:
            cols = {'data': [], 'lanc': [], 'razao': [], 'cnpj': [], 'valor': []}
            for w in ws:
                c = col(w['x0'])
                if c in cols:
                    cols[c].append(w['text'])
            linha_d = {k: ' '.join(v) for k, v in cols.items()}
            linhas_cols.append((y, linha_d))
        return linhas_cols

    def _monta_lancamentos(self, linhas_cols: List[tuple]) -> List[LancamentoBase]:

        lancamentos = [] 
        atual = None

        for y, lc in linhas_cols:
            data_txt = lc['data'].strip()
            lanc_txt = lc['lanc'].strip()
            razao_txt = lc['razao'].strip()
            valor_txt = lc['valor'].strip()

            linha_completa = ' '.join([data_txt, lanc_txt, razao_txt, valor_txt])
            if self.IGNORAR_DATA.search(linha_completa):
                if atual and atual.get('valor'):
                    lancamentos.append(atual)
                atual = None
                continue

            if self.DATA_RE.match(data_txt):
                if atual and not atual.get('valor'):

                    atual['data'] = data_txt
                    if lanc_txt:
                        atual['lanc'] = (atual['lanc'] + ' ' + lanc_txt).strip()
                    if razao_txt:
                        atual['razao'] = (atual['razao'] + ' ' + razao_txt).strip()
                    atual['valor'] = valor_txt
                else:
                    
                    if atual:
                        lancamentos.append(atual)
                    atual = {
                        'data': data_txt,
                        'lanc': lanc_txt,
                        'razao': razao_txt,
                        'valor': valor_txt,
                    }
            else:
                eh_comeco_orfao = bool(
                    lanc_txt and self.INICIO_LANC_RE.match(lanc_txt)
                    and (atual is None or atual.get('valor'))
                )
                if eh_comeco_orfao:
                    if atual and atual.get('valor'):
                        lancamentos.append(atual)
                    atual = {'data': '', 'lanc': lanc_txt, 'razao': razao_txt, 'valor': ''}
                elif atual:
                    if lanc_txt and not atual['lanc']:
                        atual['lanc'] = lanc_txt
                    elif lanc_txt:
                        atual['lanc'] += ' ' + lanc_txt
                    if razao_txt and not atual['razao']:
                        atual['razao'] = razao_txt
                    elif razao_txt:
                        atual['razao'] += ' ' + razao_txt
                    if valor_txt and not atual['valor']:
                        atual['valor'] = valor_txt

        if atual and atual.get('valor'):
            lancamentos.append(atual)

        resultado = []
        for lc in lancamentos:
            valor_txt = lc['valor'].strip()
            if not valor_txt or not self.VALOR_RE.match(valor_txt.replace(' ', '')):
                continue

            data = lc['data'][:5]  # DD/MM
            historico = (lc['lanc'] + ' ' + lc['razao']).strip()
            
            historico = re.sub(
                r'\s*\d{2,3}\.\d{3}\.\d{3}[/\-]\d{4,6}[-\s]?\d{0,2}\s*',
                ' ', historico
            ).strip()
            historico = re.sub(r'\s{2,}', ' ', historico).strip()[:100]

            if not historico or len(historico) < 3:
                continue
            if self.IGNORAR_DATA.search(historico):
                continue

            try:
                valor = float(valor_txt.replace('.', '').replace(',', '.'))
            except ValueError:
                continue

            resultado.append(LancamentoBase(data, historico, valor, self.conta_banco))

        return resultado