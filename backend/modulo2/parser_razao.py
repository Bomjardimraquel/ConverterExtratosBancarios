"""
Parser do "Razão Analítico Individual" da conta banco (Prosoft), exportado
como SpreadsheetML (XML disfarçado de .xls).
"""
import xml.etree.ElementTree as ET
import datetime
try:
    from .modelos import DespesaJaLancada
except ImportError:
    from modelos import DespesaJaLancada

_NS = {"ss": "urn:schemas-microsoft-com:office:spreadsheet"}


def _cell_text(cell) -> str:
    d = cell.find("ss:Data", _NS)
    return d.text if d is not None and d.text else ""


def parse_razao_ja_lancado(caminho: str) -> list:
    with open(caminho, "rb") as f:
        raw = f.read()
    texto = raw.decode("windows-1252")
    root = ET.fromstring(texto)
    ws = root.find("ss:Worksheet", _NS)
    table = ws.find("ss:Table", _NS)
    resultado = []
    for row in table.findall("ss:Row", _NS):
        vals = [_cell_text(c) for c in row.findall("ss:Cell", _NS)]
        if len(vals) < 9:
            continue
        docto, data_str, c_part, terc, cc, historico, debito, credito = (
            vals[1], vals[2], vals[3], vals[4], vals[5], vals[6], vals[7], vals[8]
        )
        if not data_str or "/" not in data_str:
            continue
        try:
            d, m, a = data_str.strip().split("/")
            data = datetime.date(int(a), int(m), int(d))
        except ValueError:
            continue
        if credito:
            valor, tipo = float(credito), "D"
        elif debito:
            valor, tipo = float(debito), "C"
        else:
            continue
        resultado.append(DespesaJaLancada(
            data=data, valor=valor, tipo=tipo,
            historico=historico.strip(), conta_parceira=c_part.strip(),
            terceiro=terc.strip(),
        ))
    return resultado