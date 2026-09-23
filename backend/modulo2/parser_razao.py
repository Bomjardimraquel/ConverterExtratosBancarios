"""
Parser do "Razão Analítico Individual" da conta banco (Prosoft), exportado
como SpreadsheetML (XML disfarçado de .xls).

O relatório sai do Prosoft como SpreadsheetML, mas se alguém abrir esse
arquivo no Excel e salvar de novo, ele vira um .xls binário de verdade
(formato OLE2/BIFF) — mesmo relatório, mesmas colunas, arquivo
completamente diferente por dentro. Os dois formatos acontecem na
prática, então este módulo detecta qual é (pelos bytes mágicos do OLE2
no início do arquivo) e usa o parser certo pra cada um.
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
_OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

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
        itens_ordenados = sorted(itens, key=lambda x: x.data)
        valor_total = sum(x.valor for x in itens)
        principal = min(itens, key=lambda x: len(x.historico))
        # junta os números de lançamento de todas as linhas agrupadas
        # (separados por "/"), pra não perder rastreabilidade de nenhuma
        numeros_lancamento = " / ".join(
            i.lancamento for i in itens_ordenados if i.lancamento
        )
        resultado.append(DespesaJaLancada(
            data=itens_ordenados[0].data,
            valor=valor_total,
            tipo=principal.tipo,
            historico=principal.historico + f" (+{len(itens) - 1} linha(s) de juros/multa agrupada(s))",
            conta_parceira=principal.conta_parceira,
            terceiro=principal.terceiro,
            lancamento=numeros_lancamento,
        ))
    return resultado


def _decodificar(raw: bytes) -> str:
    """
    Tenta várias codificações em sequência, em vez de assumir sempre
    windows-1252 — o Prosoft nem sempre exporta o arquivo na mesma
    codificação, e um byte fora do mapeamento do windows-1252 (ex.:
    0x81, 0x8D, 0x8F, 0x90, 0x9D) quebrava o parser inteiro. Mesmo padrão
    já usado em carregador_despesas.py e aprendizado_despesas.py.
    """
    for encoding in ("utf-8-sig", "utf-8", "windows-1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    # último recurso: nunca deixa o parser quebrar por causa de codificação
    return raw.decode("windows-1252", errors="replace")


def _e_xls_binario(caminho: str) -> bool:
    with open(caminho, "rb") as f:
        return f.read(8) == _OLE2_MAGIC


def _numero_para_texto(valor: float) -> str:
    """xlrd devolve número nativo (float) pra célula numérica — sem isso,
    um débito/crédito viraria string tipo '320.0' certo, mas um código de
    lançamento inteiro viraria '12345.0' errado. Converte pra int quando
    o valor é um número inteiro, senão mantém a representação decimal
    mais curta (sem notação científica pra magnitudes normais)."""
    if valor == int(valor):
        return str(int(valor))
    return repr(valor)


def _linhas_do_xml(caminho: str):
    with open(caminho, "rb") as f:
        raw = f.read()
    texto = _decodificar(raw)
    root = ET.fromstring(texto)
    ws = root.find("ss:Worksheet", _NS)
    table = ws.find("ss:Table", _NS)
    for row in table.findall("ss:Row", _NS):
        yield [_cell_text(c) for c in row.findall("ss:Cell", _NS)]


def _linhas_do_binario(caminho: str):
    import xlrd

    wb = xlrd.open_workbook(caminho)
    sh = wb.sheet_by_index(0)
    for r in range(sh.nrows):
        linha = []
        for c in range(sh.ncols):
            tipo = sh.cell_type(r, c)
            valor = sh.cell_value(r, c)
            if tipo == xlrd.XL_CELL_EMPTY:
                valor = ""
            elif tipo == xlrd.XL_CELL_DATE:
                valor = xlrd.xldate_as_datetime(valor, wb.datemode).strftime("%d/%m/%Y")
            elif tipo == xlrd.XL_CELL_NUMBER:
                valor = _numero_para_texto(valor)
            else:
                valor = str(valor) if valor not in (None, "") else ""
            linha.append(valor)
        yield linha


def parse_razao_ja_lancado(caminho: str) -> list:
    linhas = _linhas_do_binario(caminho) if _e_xls_binario(caminho) else _linhas_do_xml(caminho)
    resultado = []
    for vals in linhas:
        if len(vals) < 9:
            continue
        lcto, docto, data_str, c_part, terc, cc, historico, debito, credito = (
            vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], vals[6], vals[7], vals[8]
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
            terceiro=terc.strip(), lancamento=lcto.strip(),
        ))
    return agrupar_duplicatas_com_juros(resultado)