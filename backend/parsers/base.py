import re
import unicodedata
from utils.classificador import classificar_lancamento
from utils.contas import CONTAS


def normalizar(texto: str) -> str:
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def nome_banco(conta_banco: str) -> str:
    nomes = {
        "11041": "Banco do Brasil",
        "11142": "BB Rende Fácil",
        "21381": "Banco do Brasil",
        "11120": "Sicoob",
        "21325": "Sicoob",
        "11045": "Itaú",
        "11146": "Itaú",
        "11127": "PagBank",
        "11126": "Santander",
        "11044": "Bradesco",
        "11042": "Banco do Nordeste",
    }
    return nomes.get(conta_banco, CONTAS.get(conta_banco, conta_banco))


def _extrair_nome_pix(descricao: str) -> str:
    prefixos = [
        r"PIX RECEB\.OUTRA IF\s*[-–]?\s*Recebimento Pix\s*",
        r"PIX RECEBIDO\s*[-–]?\s*OUTRA IF\s*[-–]?\s*Recebimento Pix\s*",
        r"TRANSF\.RECEBIDA\s*[-–]?\s*PIX SICOOB\s*[-–]?\s*",
        r"TRANSF\. RECEB\.\s*[-–]?\s*PIX SI[^\s]*\s*[-–]?\s*",
        r"PIX\s*[-–]\s*Recebido\s*",
        r"PIX RECEBIDO\s+\w+\d+/\d+\s+",
        r"Recebimento Pix\s*",
        r"REM\.:\s*",
        r"CRED\.TR\.CT\.INTERCRE\s*[-–]?\s*",
        r"CRÉD\.TED[-–]STR\s*[-–]?\s*",
        r"CRÉD\.TR\.CT\.INTERCRE\s*[-–]?\s*",
    ]
    texto = descricao
    for pat in prefixos:
        texto = re.sub(pat, "", texto, flags=re.IGNORECASE).strip()
    texto = re.sub(r"^[-–\s]+", "", texto).strip()
    texto = re.sub(r"\*{3}\.\d{3}\.\d{3}-\*{2}", "", texto).strip()
    texto = re.sub(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", "", texto).strip()
    texto = re.sub(r"\b\d{10,}\b", "", texto).strip()
    texto = re.sub(r"\b\d{2}\.\d{3}\.\d{3}\.\d{3}\.\d{3}\b", "", texto).strip()
    texto = re.sub(r"DOC\.:\s*\w+", "", texto, flags=re.IGNORECASE).strip()
    texto = re.sub(r"[-–\s]+$", "", texto).strip()
    texto = re.sub(r"\s+", " ", texto).strip()
    if len(texto) < 3 or re.match(r"^[\d\s\.\-]+$", texto):
        return ""
    return texto[:50].strip()


# ── Tabela de regras de formatação da descrição ─────────────────────────────
#
# Isso NUNCA afeta a leitura/classificação/cruzamento do extrato — é só
# cosmético, pra deixar a descrição bonita no Excel do Módulo 1. O dado cru
# (usado pelo Módulo 2 pra casar título/despesa) fica intacto em `.raw`,
# separado disso.
#
# Cada regra é um dicionário com "tipo":
#   "keyword"       → dispara se alguma palavra de "match" aparece na
#                      descrição normalizada, não importa a classificação
#   "classificacao" → dispara se `classificacao` (vinda do classificador.py)
#                      bate exatamente com "match"
#   "pix_recebido"  → igual "keyword", mas usa `_extrair_nome_pix` pra
#                      montar o texto (precisa de tratamento à parte)
#
# Ordem importa: a primeira regra que bater é usada. Pra adicionar/corrigir
# uma regra (ex: mudar o texto do IOF, ou criar uma pra aplicação do BB),
# mexe só aqui — não precisa tocar em formatar_descricao().
REGRAS_DESCRICAO = [
    # ── Boleto ───────────────────────────────────────────────────────────
    {
        "tipo": "keyword",
        "match": [
            "boleto", "pagamento de boleto", "boleto pago", "pg. boleto",
            "deb.tit.compe", "déb.tit.compe", "tit.compe efetivado",
            "cheque compe", "cheque pago", "deb. pagamento de boleto",
        ],
        "template": "Pg. ref. boleto conf. extrato",
    },

    # ── Por classificação (vem de classificar_lancamento) ───────────────────
    {"tipo": "classificacao", "match": "Despesas Bancárias", "template": "Vr.deb.n/cta.{banco} ref.desp bancarias"},
    {"tipo": "classificacao", "match": "Juros",              "template": "Vr.deb.n/cta.{banco} ref.juros"},
    {"tipo": "classificacao", "match": "IOF",                "template": "Vr.deb.n/cta.{banco} ref.iof"},

    # ── Contas especiais do BB (empréstimo Giro/Pronampe, Rende Fácil) ──────
    # Usam "Vr. ref." pros dois lados (entrada E saída) — diferente do
    # padrão comum, onde entrada vira "Vr. recebido de..." — porque aqui
    # não é uma receita/despesa de verdade, é só transferência de saldo.
    {"tipo": "classificacao", "match": "Empréstimo BB (Giro/Pronampe)", "template": "Vr. ref. {descricao} conf. extrato"},
    {"tipo": "classificacao", "match": "BB Rende Fácil (Aplicação)",    "template": "Vr. ref. {descricao} conf. extrato"},

    # TODO: regras específicas do BB (aplicação automática / BB Rende Fácil
    # etc) entram aqui — aguardando a Raquel mandar o texto/conta que ela
    # quer pra cada uma. Exemplo de como ficaria (ajustar quando ela mandar):
    # {
    #     "tipo": "keyword",
    #     "match": ["bb rende facil", "rende facil"],
    #     "template": "Vr. ref. aplicação automática conf. extrato",
    # },

    # ── Pix recebido (usa extração de nome) ─────────────────────────────────
    {
        "tipo": "pix_recebido",
        "match": [
            "pix receb", "pix recebido", "pix - recebido",
            "transf.recebida", "transf. receb", "cred.tr.ct",
            "créd.tr.ct", "cred.ted", "créd.ted",
            "pix rejeita",
        ],
    },
]


def formatar_descricao(descricao: str, valor: float, conta_banco: str, classificacao: str) -> str:
    desc_norm = normalizar(descricao)
    banco = nome_banco(conta_banco)
    eh_credito = valor >= 0

    for regra in REGRAS_DESCRICAO:
        tipo = regra["tipo"]

        if tipo == "keyword":
            if any(kw in desc_norm for kw in regra["match"]):
                return regra["template"]

        elif tipo == "classificacao":
            if classificacao == regra["match"]:
                return regra["template"].format(banco=banco, descricao=descricao)

        elif tipo == "pix_recebido":
            if any(kw in desc_norm for kw in regra["match"]):
                nome = _extrair_nome_pix(descricao)
                if nome:
                    return f"Vr. ref. pix recebido de {nome} conf. extrato"
                return "Vr. ref. pix recebido conf. extrato"

    # ── Fallback genérico (nenhuma regra bateu) ─────────────────────────────
    if eh_credito:
        return f"Vr. recebido de {descricao} conf. extrato"
    return f"Vr. ref. {descricao} conf. extrato"


class LancamentoBase:
    def __init__(self, data: str, descricao: str, valor: float, conta_banco: str):
        self.data = data
        self.valor = valor
        self.conta_banco = conta_banco

        resultado = classificar_lancamento(descricao, valor, conta_banco)
        self.tipo = resultado["tipo"]
        self.conta_debito = resultado["conta_debito"]
        self.conta_credito = resultado["conta_credito"]
        self.classificacao = resultado["classificacao"]
        self.requer_revisao = resultado["requer_revisao"]

        # Texto ORIGINAL do extrato (histórico + detalhe, antes de qualquer
        # formatação) — o Módulo 1 não usa isso (usa .descricao, formatado
        # abaixo), mas o Módulo 2 precisa do texto bruto pra casar título e
        # regra de texto. Ver bug 4.6 do documento de contexto: sem isso,
        # formatar_descricao troca pagamento de boleto por uma string
        # genérica fixa, jogando fora o nome do fornecedor.
        self.raw = descricao

        self.descricao = formatar_descricao(descricao, valor, conta_banco, self.classificacao)

    def to_dict(self):
        return {
            "data": self.data,
            "descricao": self.descricao,
            "raw": self.raw,
            "valor": abs(self.valor),
            "tipo": self.tipo,
            "conta_debito": self.conta_debito,
            "conta_credito": self.conta_credito,
            "classificacao": self.classificacao,
            "requer_revisao": self.requer_revisao,
        }


class ParserBase:
    def __init__(self, conta_banco: str):
        self.conta_banco = conta_banco

    def parse(self, conteudo: bytes):
        raise NotImplementedError