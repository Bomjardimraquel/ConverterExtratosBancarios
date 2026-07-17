"""
Modelos SQLModel — cada classe aqui é uma tabela no Postgres. Segue o
desenho (ERD) que já validamos, sem mudar a estrutura.

SQLModel é construído em cima do SQLAlchemy (mesmo motor por baixo, sem
diferença de performance) — só junta a "classe que representa a tabela"
com a "classe que valida os dados" numa coisa só, economizando código
duplicado em relação a escrever SQLAlchemy puro.
"""
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class Empresa(SQLModel, table=True):
    __tablename__ = "empresas"

    # o id continua sendo o código que a Raquel já usa (A25, D08...),
    # não um número — mais fácil de reconhecer olhando o banco direto
    id: str = Field(primary_key=True)
    nome: str
    cnpj: Optional[str] = None
    grupo: str                       # "comercio" | "servicos"
    regime: str                      # "simples" | "lucro_presumido"
    conta_caixa: str = "11002"
    conta_clientes: str
    conta_fornecedores: str
    conta_aplicacao: Optional[str] = None
    conta_saida_sem_match: Optional[str] = None
    casa_pf: bool = False
    tolerancia_valor: float = 0.02
    janela_dias_despesa: int = 3
    janela_dias_titulo_pj: int = 30

    bancos: List["EmpresaBanco"] = Relationship(back_populates="empresa")
    terceiros: List["EmpresaTerceiro"] = Relationship(back_populates="empresa")
    regras: List["EmpresaRegra"] = Relationship(back_populates="empresa")
    intermediarios: List["EmpresaIntermediario"] = Relationship(back_populates="empresa")
    ignorar_despesas: List["EmpresaIgnorarDespesa"] = Relationship(back_populates="empresa")


class EmpresaBanco(SQLModel, table=True):
    __tablename__ = "empresa_bancos"

    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: str = Field(foreign_key="empresas.id")
    banco_key: str      # "sicoob", "bb", "itau"...
    conta_banco: str    # "11120", "11041"...

    empresa: Empresa = Relationship(back_populates="bancos")


class EmpresaTerceiro(SQLModel, table=True):
    __tablename__ = "empresa_terceiros"

    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: str = Field(foreign_key="empresas.id")
    tipo: str          # "cliente" | "fornecedor"
    nome: str          # a chave usada pra bater prefixo com o título
    codigo: str

    empresa: Empresa = Relationship(back_populates="terceiros")


class EmpresaRegra(SQLModel, table=True):
    __tablename__ = "empresa_regras"

    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: str = Field(foreign_key="empresas.id")
    contexto: str = "extrato"   # "extrato" (regras_texto) | "despesa_bruta" (regras_extras)
    ordem: int = 0
    modo_match: str = "contem"  # "contem" | "contem_todos"
    conta_debito: Optional[str] = None
    conta_credito: Optional[str] = None
    usa_padrao: bool = False
    descricao: Optional[str] = None
    descricao_template: Optional[str] = None
    descricao_sem_nome: Optional[str] = None
    descricao_dinamica: bool = False
    confianca: str = "media"
    aviso: str = ""

    empresa: Empresa = Relationship(back_populates="regras")
    termos: List["EmpresaRegraTermo"] = Relationship(back_populates="regra")


class EmpresaRegraTermo(SQLModel, table=True):
    __tablename__ = "empresa_regra_termos"

    id: Optional[int] = Field(default=None, primary_key=True)
    regra_id: int = Field(foreign_key="empresa_regras.id")
    termo: str
    tipo: str = "contem"   # "contem" | "nao_contem"

    regra: EmpresaRegra = Relationship(back_populates="termos")


class EmpresaIntermediario(SQLModel, table=True):
    __tablename__ = "empresa_intermediarios"

    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: str = Field(foreign_key="empresas.id")
    nome: str

    empresa: Empresa = Relationship(back_populates="intermediarios")


class EmpresaIgnorarDespesa(SQLModel, table=True):
    __tablename__ = "empresa_ignorar_despesa"

    id: Optional[int] = Field(default=None, primary_key=True)
    empresa_id: str = Field(foreign_key="empresas.id")
    termo: str

    empresa: Empresa = Relationship(back_populates="ignorar_despesas")