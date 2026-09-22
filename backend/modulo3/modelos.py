from dataclasses import dataclass, field
from datetime import date
from typing import Optional

GRUPOS_VALIDOS = ("ativo", "passivo", "despesas", "receitas")
_GRUPO_POR_PRIMEIRO_DIGITO = {"1": "ativo", "2": "passivo", "5": "despesas", "6": "receitas"}


@dataclass
class Lancamento:
    data: date
    historico: str
    debito: float
    credito: float
    lancamento: Optional[str] = None   # nº do lote/LCTO, pra achar no Prosoft depois
    docto: Optional[str] = None


@dataclass
class BlocoConta:
    
    acesso: str
    classificador: str
    nome: str
    terceiro_id: Optional[str]
    terceiro_nome: Optional[str]
    
    saldo_final: float
    debito_total: float
    credito_total: float
    lancamentos: list  # list[Lancamento]

    @property
    def grupo(self) -> str:
        return _GRUPO_POR_PRIMEIRO_DIGITO.get(self.acesso[:1], "desconhecido")

    @property
    def tem_terceiro(self) -> bool:
        return self.terceiro_id is not None


@dataclass
class Achado:
    grupo: str                  # ativo | passivo | despesas | receitas
    acesso: str
    nome_conta: str
    tipo: str                   # chave curta da regra que gerou (pra filtrar/testar)
    descricao: str
    severidade: str             # OK | Baixo | Médio | Alto
    terceiro: Optional[str] = None
    valor: Optional[float] = None
    referencia: Optional[str] = None   # nº de lote/lançamento, quando aplicável