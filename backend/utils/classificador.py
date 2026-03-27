import unicodedata
import re
from utils.contas import REGRAS_CLASSIFICACAO, CONTA_CAIXA


def normalizar(texto: str) -> str:
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto


def classificar_lancamento(descricao: str, valor: float, conta_banco: str) -> dict:
    """
    Regras:
    - Crédito (valor >= 0): débita banco → credita caixa (11002)
    - Débito geral (valor < 0): débita caixa (11002) → credita banco
    - Débito especial (despesa bancária, IOF, juros, imposto):
        débita conta_despesa → credita banco
    """
    desc_norm = normalizar(descricao)
    eh_credito = valor >= 0

    if not eh_credito:
        for regra in REGRAS_CLASSIFICACAO:
            for kw in regra["keywords"]:
                if normalizar(kw) in desc_norm:
                    return {
                        "tipo": "Débito",
                        "conta_debito": regra["conta_despesa"],
                        "conta_credito": conta_banco,
                        "classificacao": regra["nome"],
                        "requer_revisao": False,
                    }

    if eh_credito:
        return {
            "tipo": "Crédito",
            "conta_debito": conta_banco,
            "conta_credito": CONTA_CAIXA,
            "classificacao": "Receita / Entrada",
            "requer_revisao": False,
        }
    else:
        return {
            "tipo": "Débito",
            "conta_debito": CONTA_CAIXA,
            "conta_credito": conta_banco,
            "classificacao": "Pagamento / Saída",
            "requer_revisao": False,
        }
