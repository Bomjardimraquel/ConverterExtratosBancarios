
import re
import xml.etree.ElementTree as ET
import datetime
from typing import Optional

try:
    from .modelos import BlocoConta, Lancamento
except ImportError:
    from modelos import BlocoConta, Lancamento

_NS = {"ss": "urn:schemas-microsoft-com:office:spreadsheet"}
_NS_INDEX = "{urn:schemas-microsoft-com:office:spreadsheet}Index"

# "Conta:  21408  2104080000  Cofins a Recolher" ou, com sub-razão,
# "Conta:  11401  1109010100  CLIENTES DIVERSOS   Ter.: 013950-NOME DO TERCEIRO"
_CABECALHO_RE = re.compile(
    r"Conta:\s*(?P<acesso>\S+)\s+(?P<classificador>\S+)\s+(?P<nome>.*?)"
    r"(?:\s+Ter\.:\s*(?P<terc_id>\d+)-(?P<terc_nome>.*))?$"
)


class RazaoParseError(Exception):
    pass


def _linha_para_celulas(row) -> list:
    """
    Reconstrói a linha inteira respeitando o atributo ss:Index — o
    SpreadsheetML pula célula vazia em vez de escrever uma vazia, então
    sem isso as colunas desalinham silenciosamente (foi assim que o
    Saldo Anterior saiu 100x maior num teste desta sessão).
    """
    celulas = []
    idx = 0
    for cell in row.findall("ss:Cell", _NS):
        idx_attr = cell.get(_NS_INDEX)
        if idx_attr:
            idx = int(idx_attr) - 1
        while len(celulas) < idx:
            celulas.append(None)
        data = cell.find("ss:Data", _NS)
        celulas.append(data.text if data is not None else None)
        idx += 1
    return celulas


def _to_float(v) -> float:
    if v is None or v == "":
        return 0.0
    return float(v)


def _parse_saldo_virgula(v) -> Optional[float]:
    """Formato "1.234,56" -> 1234.56. Só usado como fallback."""
    if v is None:
        return None
    return float(v.replace(".", "").replace(",", "."))


def _parse_data(v) -> Optional[datetime.date]:
    if not v or "/" not in v:
        return None
    try:
        d, m, a = v.strip().split("/")
        return datetime.date(int(a), int(m), int(d))
    except ValueError:
        return None


def _com_sinal(valor: float, dc: Optional[str]) -> float:
    """Devolve o valor já assinado: positivo = D, negativo = C."""
    return -valor if dc == "C" else valor


_META_ROTULOS = {
    "Empresa:": "empresa",
    "CNPJ:": "cnpj",
    "Período:": "periodo",
    "Data de Emissão:": "data_emissao",
}


def parse_metadados(caminho: str) -> dict:
    """
    Lê só as ~5 primeiras linhas do relatório (empresa, CNPJ, período,
    data de emissão). Rótulo e valor vêm em células XML separadas na
    mesma linha, por isso reaproveita o parse de célula em vez de regex
    no texto cru (rótulo e valor nunca ficam no mesmo nó <Data>).
    """
    with open(caminho, "rb") as f:
        raw = f.read()
    texto = raw.decode("cp1252")
    root = ET.fromstring(texto)
    ws = root.find("ss:Worksheet", _NS)
    table = ws.find("ss:Table", _NS) if ws is not None else None

    meta = {"empresa": None, "cnpj": None, "periodo": None, "data_emissao": None}
    if table is None:
        return meta

    for row in table.findall("ss:Row", _NS)[:6]:
        celulas = _linha_para_celulas(row)
        for i, valor in enumerate(celulas):
            if valor in _META_ROTULOS and i + 1 < len(celulas):
                meta[_META_ROTULOS[valor]] = celulas[i + 1]

    if meta["data_emissao"]:
        meta["data_emissao"] = _parse_data(meta["data_emissao"])
    return meta


def parse_razao(caminho: str) -> list:
    """
    Lê o arquivo inteiro e devolve list[BlocoConta] — um por Conta:/
    Terceiro encontrado, na ordem em que aparecem no arquivo.
    """
    with open(caminho, "rb") as f:
        raw = f.read()
    try:
        texto = raw.decode("cp1252")
    except UnicodeDecodeError as e:
        raise RazaoParseError(f"Não consegui decodificar o arquivo como cp1252: {e}")

    try:
        root = ET.fromstring(texto)
    except ET.ParseError as e:
        raise RazaoParseError(
            f"Arquivo não é um SpreadsheetML válido (razão do Prosoft esperado): {e}"
        )

    ws = root.find("ss:Worksheet", _NS)
    table = ws.find("ss:Table", _NS) if ws is not None else None
    if table is None:
        raise RazaoParseError("Não achei a planilha dentro do XML — formato inesperado.")

    blocos = []
    bloco_atual = None
    lancamentos_atuais = []

    for row in table.findall("ss:Row", _NS):
        celulas = _linha_para_celulas(row)
        if not celulas or all(c is None for c in celulas):
            continue

        primeira = celulas[0] if celulas else None
        if primeira and str(primeira).startswith("Conta:"):
            if bloco_atual is not None:
                bloco_atual.lancamentos = lancamentos_atuais
                blocos.append(bloco_atual)

            m = _CABECALHO_RE.match(str(primeira).strip())
            if not m:
                raise RazaoParseError(f"Cabeçalho de conta em formato inesperado: {primeira!r}")

            bloco_atual = BlocoConta(
                acesso=m.group("acesso").strip(),
                classificador=m.group("classificador").strip(),
                nome=m.group("nome").strip(),
                terceiro_id=m.group("terc_id"),
                terceiro_nome=(m.group("terc_nome") or "").strip() or None,
                saldo_anterior=0.0, saldo_final=0.0,
                debito_total=0.0, credito_total=0.0,
                lancamentos=[],
            )
            lancamentos_atuais = []
            continue

        if bloco_atual is None:
            continue  # linhas de cabeçalho do relatório (empresa, período...), ignora

        col_historico = celulas[6] if len(celulas) > 6 else None
        dc = celulas[10] if len(celulas) > 10 else None

        if col_historico == "SALDO ANTERIOR":
            deb_col = celulas[7] if len(celulas) > 7 else None
            valor = _to_float(deb_col) if deb_col else (_parse_saldo_virgula(celulas[9]) or 0.0)
            bloco_atual.saldo_anterior = _com_sinal(valor, dc)
            continue

        if col_historico == "SALDO FINAL":
            bloco_atual.debito_total = _to_float(celulas[7] if len(celulas) > 7 else None)
            bloco_atual.credito_total = _to_float(celulas[8] if len(celulas) > 8 else None)
            sf = _parse_saldo_virgula(celulas[9] if len(celulas) > 9 else None) or 0.0
            bloco_atual.saldo_final = _com_sinal(sf, dc)
            continue

        # linha de lançamento normal
        data = _parse_data(celulas[2] if len(celulas) > 2 else None)
        if data is None:
            continue  # linha em branco/separador dentro do bloco
        lancamentos_atuais.append(Lancamento(
            data=data,
            historico=(col_historico or "").strip(),
            debito=_to_float(celulas[7] if len(celulas) > 7 else None),
            credito=_to_float(celulas[8] if len(celulas) > 8 else None),
            lancamento=(celulas[0] or "").strip() or None,
            docto=(celulas[1] or "").strip() or None,
        ))

    if bloco_atual is not None:
        bloco_atual.lancamentos = lancamentos_atuais
        blocos.append(bloco_atual)

    if not blocos:
        raise RazaoParseError("Não encontrei nenhum bloco 'Conta:' no arquivo.")

    return blocos