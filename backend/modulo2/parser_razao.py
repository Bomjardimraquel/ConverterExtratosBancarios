"""
Parser do "Razão Analítico Individual" da conta banco (Prosoft), exportado
como SpreadsheetML (XML disfarçado de .xls).
"""
import re
import xml.etree.ElementTree as ET
import datetime
from collections import defaultdict
try:
    from .modelos import DespesaJaLancada
except ImportError:
    from modelos import DespesaJaLancada

_NS = {"ss": "urn:schemas-microsoft-com:office:spreadsheet"}

# Casa "duplic.n. 13801066-003", "duplic. n 13801066-003" etc — o número
# que segue "duplic" (com ou sem ponto) e "n" (com ou sem ponto).
_DUPLICATA_RE = re.compile(r"duplic\.?\s*n\.?\s*([\d\-]+)", re.IGNORECASE)


def _cell_text(cell) -> str:
    d = cell.find("ss:Data", _NS)
    return d.text if d is not None and d.text else ""


def _extrair_numero_duplicata(historico: str):
    m = _DUPLICATA_RE.search(historico or "")
    return m.group(1) if m else None


def agrupar_duplicatas_com_juros(lista: list) -> list:
    """
    No razão, o pagamento principal de uma duplicata ("Pg.duplic.n. X")
    e o juro/multa dela ("Pg.juros/multa s/duplic.n. X") entram como duas
    linhas separadas — mas no banco, o pagamento geralmente sai JUNTO,
    num valor só. Sem juntar essas duas linhas antes, nenhuma das duas
    bate sozinha contra o extrato (o valor de cada uma isolada nunca é
    igual ao valor real debitado). Essa função junta linhas que
    referenciam a MESMA duplicata, somando o valor, antes do motor tentar
    casar com o extrato.
    """
    por_duplicata = defaultdict(list)
    sem_duplicata = []

    for item in lista:
        numero = _extrair_numero_duplicata(item.historico)
        if numero:
            por_duplicata[numero].append(item)
        else:
            sem_duplicata.append(item)

    resultado = list(sem_duplicata)
    for numero, itens in por_duplicata.items():
        if len(itens) == 1:
            resultado.append(itens[0])
            continue
        # mais de uma linha pra mesma duplicata (principal + juros/multa)
        # — soma tudo, usa a data mais antiga, mantém o histórico mais
        # curto como "principal" (o de juros/multa costuma ser mais longo,
        # por causa do "juros/multa s/" na frente)
        itens_ordenados = sorted(itens, key=lambda x: x.data)
        valor_total = sum(x.valor for x in itens)
        principal = min(itens, key=lambda x: len(x.historico))
        resultado.append(DespesaJaLancada(
            data=itens_ordenados[0].data,
            valor=valor_total,
            tipo=principal.tipo,
            historico=principal.historico + f" (+{len(itens) - 1} linha(s) de juros/multa agrupada(s))",
            conta_parceira=principal.conta_parceira,
            terceiro=principal.terceiro,
        ))
    return resultado


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
    return agrupar_duplicatas_com_juros(resultado)