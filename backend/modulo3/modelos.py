"""
Modelos de dado do Módulo 3. Sem SQLModel aqui de propósito — nada disso
vai pro banco, é só a estrutura em memória entre o parser, o motor e a
resposta da API (mesmo espírito do modulo2/modelos.py).
"""
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
    """
    Um bloco "Conta:" do razão. Quando a conta tem sub-razão por Terceiro
    (Clientes, Fornecedores), cada Terceiro vira um BlocoConta próprio,
    todos com o mesmo `acesso`/`classificador` — é assim que a gente
    detecta "conta com Terceiro" (mais de um bloco repetindo o acesso).
    """
    acesso: str
    classificador: str
    nome: str
    terceiro_id: Optional[str]
    terceiro_nome: Optional[str]
    # já com sinal: positivo = D (devedor), negativo = C (credor) — mesma
    # convenção usada em toda a análise que fizemos nesta conversa
    saldo_anterior: float
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