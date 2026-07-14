import pdfplumber
import re
import io
from parsers.base import ParserBase, LancamentoBase
from typing import List


class ParserItau(ParserBase):
    """
    Itaú — lê o PDF por posição de palavras (x,y) em vez de por linhas de texto.

    Colunas fixas no PDF:
      x ~  35 → Data (DD/MM/AAAA)
      x ~  91 → Lançamento
      x ~ 227 → Razão Social
      x ~ 364 → CNPJ/CPF
      x ~ 472 → Valor (R$)
      x ~ 520 → Saldo (R$)  ← ignorado

    Cada lançamento pode ocupar 2-3 sublinhas com y ligeiramente diferente.
    Agrupa palavras por janela de y (~14pt) para reconstruir cada linha lógica,
    depois associa linhas de mesma Data ou sem Data à data corrente.
    """

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
    # Prefixos que sinalizam o INÍCIO de um lançamento de verdade (a
    # coluna "Lançamento") — usado pra diferenciar uma linha sem data que
    # é o começo órfão de um lançamento novo (cortado bem na quebra de
    # página) de uma linha sem data que é só continuação do lançamento
    # atual (o código do documento, tipo "DB0087118734"/"AT0087118734").
    INICIO_LANC_RE = re.compile(
        r"^(RECEBIMENTO|RECEBIMENTOS|BOLETO|BOLETOS|PIX|RENDIMENTOS?|"
        r"PAGAMENTOS?|SALDO|TARIFA|D[ÉE]BITO|CR[ÉE]DITO|RESGATE|"
        r"APLICA[ÇC][ÃA]O|TRANSFER[ÊE]NCIA|CHEQUE)",
        re.IGNORECASE
    )

    # Limites X das colunas (tolerância ±30)
    X_DATA    = (20,  80)
    X_LANC    = (81, 220)
    X_RAZAO   = (221, 360)
    X_CNPJ    = (361, 460)
    X_VALOR   = (461, 570)

    def parse(self, conteudo: bytes) -> List[LancamentoBase]:
        # Monta as "linhas-coluna" de TODAS as páginas numa lista só, na
        # ordem de leitura, ANTES de agrupar em lançamentos. Um lançamento
        # pode ser partido bem na quebra de página (a linha com
        # Lançamento/Razão Social fica na última linha de uma página, e a
        # linha com Data/Valor só chega na primeira linha da página
        # seguinte). Processar página por página e reiniciar o estado a
        # cada página fazia o pedaço órfão do fim de uma página grudar no
        # lançamento ANTERIOR (ainda não finalizado) em vez do lançamento
        # a que pertence de verdade — corrompendo dois lançamentos por
        # quebra de página: um ficava com texto de sobra grudado, o outro
        # nascia incompleto.
        linhas_cols_doc: List[tuple] = []
        with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
            for page in pdf.pages:
                linhas_cols_doc.extend(self._linhas_cols_da_pagina(page))
        return self._monta_lancamentos(linhas_cols_doc)

    def _linhas_cols_da_pagina(self, page) -> List[tuple]:
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        if not words:
            return []

        # Agrupa palavras em "linhas físicas" por proximidade de y (janela 8pt)
        linhas_fisicas = []  # [(y_centro, [word, ...])]
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

        # Para cada linha física, classifica palavras por coluna
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

        # Monta lançamentos: agrupa linhas consecutivas que pertencem ao mesmo lançamento
        # Uma linha tem data → início de novo lançamento
        # Uma linha sem data → complemento do lançamento anterior (razão social em 2ª linha)
        lancamentos = []  # [(data, lanc, razao, valor)]
        atual = None

        for y, lc in linhas_cols:
            data_txt = lc['data'].strip()
            lanc_txt = lc['lanc'].strip()
            razao_txt = lc['razao'].strip()
            valor_txt = lc['valor'].strip()

            # Ignora linhas de cabeçalho/saldo
            linha_completa = ' '.join([data_txt, lanc_txt, razao_txt, valor_txt])
            if self.IGNORAR_DATA.search(linha_completa):
                if atual and atual.get('valor'):
                    lancamentos.append(atual)
                atual = None
                continue

            if self.DATA_RE.match(data_txt):
                if atual and not atual.get('valor'):
                    # 'atual' é um começo pendente (rótulo órfão que veio
                    # antes, possivelmente na página anterior) — completa
                    # ELE com a data/cnpj/valor desta linha em vez de
                    # começar um lançamento do zero e perder o rótulo.
                    atual['data'] = data_txt
                    if lanc_txt:
                        atual['lanc'] = (atual['lanc'] + ' ' + lanc_txt).strip()
                    if razao_txt:
                        atual['razao'] = (atual['razao'] + ' ' + razao_txt).strip()
                    atual['valor'] = valor_txt
                else:
                    # Nova linha com data → salva o anterior, começa novo
                    if atual:
                        lancamentos.append(atual)
                    atual = {
                        'data': data_txt,
                        'lanc': lanc_txt,
                        'razao': razao_txt,
                        'valor': valor_txt,
                    }
            else:
                # Linha sem data: pode ser (a) começo órfão de um
                # lançamento novo, cortado bem na quebra de página — a
                # Data só chega numa linha seguinte — ou (b) continuação
                # normal do lançamento atual (código do documento). O
                # sinal pra diferenciar: começo órfão tem um rótulo
                # reconhecível de tipo de lançamento (RECEBIMENTO, BOLETO,
                # PIX...) na coluna Lançamento; continuação normal não
                # (é só o código do documento, tipo "DB0087118734").
                eh_comeco_orfao = bool(
                    lanc_txt and self.INICIO_LANC_RE.match(lanc_txt)
                    and (atual is None or atual.get('valor'))
                )
                if eh_comeco_orfao:
                    if atual and atual.get('valor'):
                        lancamentos.append(atual)
                    atual = {'data': '', 'lanc': lanc_txt, 'razao': razao_txt, 'valor': ''}
                elif atual:
                    # continuação normal (coluna Lançamento ou Razão Social)
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

        # Converte para LancamentoBase
        resultado = []
        for lc in lancamentos:
            valor_txt = lc['valor'].strip()
            if not valor_txt or not self.VALOR_RE.match(valor_txt.replace(' ', '')):
                continue

            data = lc['data'][:5]  # DD/MM
            historico = (lc['lanc'] + ' ' + lc['razao']).strip()
            # Remove CNPJ/CPF residual
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