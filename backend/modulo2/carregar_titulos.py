"""
Carrega o relatório de títulos do Prosoft (Data only, com Baixados).

Formato: .xls binário (lido via xlrd, não confundir com o SpreadsheetML
do razão — são formatos completamente diferentes apesar dos dois usarem
extensão .xls). Sem cabeçalho, 7 colunas sempre na mesma ordem:

    CNPJ/CPF | Nome | Docto | Vencimento (serial Excel) | Valor |
    Data Pagto (serial Excel ou vazio) | Dias de atraso

"Data Pagto" vazio = título em aberto. Preenchido = já baixado no Prosoft.
"""
import io
import datetime
import xlrd

try:
    from .modelos import Titulo
except ImportError:
    from modelos import Titulo


def _xldate(serial) -> datetime.date:
    return datetime.date(1899, 12, 30) + datetime.timedelta(days=int(serial))


def carregar_titulos(caminho_ou_bytes, tipo: str = "receber") -> list:
    """
    tipo: "receber" (títulos a receber, ex: titulos_receber_a25.xls) ou
          "pagar" (duplicatas/títulos a pagar, ex: duplicatas_d08.xls).
    """
    if isinstance(caminho_ou_bytes, (bytes, bytearray)):
        wb = xlrd.open_workbook(file_contents=caminho_ou_bytes)
    else:
        wb = xlrd.open_workbook(caminho_ou_bytes)

    sh = wb.sheet_by_index(0)
    titulos = []
    for r in range(sh.nrows):
        vals = [sh.cell_value(r, c) for c in range(7)]
        cnpj, nome, docto, vencto, valor, data_pagto, atraso = vals
        if not isinstance(vencto, (int, float)) or not isinstance(valor, (int, float)):
            continue
        pago = isinstance(data_pagto, (int, float)) and data_pagto > 0
        titulos.append(Titulo(
            cnpj_cpf=str(cnpj).strip(), nome=str(nome), docto=str(docto),
            vencimento=_xldate(vencto), valor=float(valor),
            pago=pago, data_pagto=_xldate(data_pagto) if pago else None,
            tipo=tipo,
        ))
    return titulos