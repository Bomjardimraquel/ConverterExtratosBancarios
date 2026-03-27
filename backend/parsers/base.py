from abc import ABC, abstractmethod
from typing import List
from utils.classificador import classificar_lancamento


class LancamentoBase:
    def __init__(self, data: str, descricao: str, valor: float, conta_banco: str):
        self.data = data
        self.descricao = descricao
        self.valor = valor
        self.conta_banco = conta_banco
        classificacao = classificar_lancamento(descricao, valor, conta_banco)
        self.tipo = classificacao["tipo"]
        self.conta_debito = classificacao["conta_debito"]
        self.conta_credito = classificacao["conta_credito"]
        self.classificacao = classificacao["classificacao"]
        self.requer_revisao = classificacao["requer_revisao"]

    def to_dict(self):
        return {
            "data": self.data,
            "descricao": self.descricao,
            "valor": abs(self.valor),
            "tipo": self.tipo,
            "conta_debito": self.conta_debito,
            "conta_credito": self.conta_credito,
            "classificacao": self.classificacao,
            "requer_revisao": self.requer_revisao,
        }


class ParserBase(ABC):
    def __init__(self, conta_banco: str):
        self.conta_banco = conta_banco

    @abstractmethod
    def parse(self, conteudo: bytes) -> List[LancamentoBase]:
        pass
