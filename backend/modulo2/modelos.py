"""
Estruturas de dados do Módulo 2 (cruzamento).
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class LancamentoBanco:
    data: date
    historico: str
    detalhe: str
    valor: float
    tipo: str


@dataclass
class Titulo:
    cnpj_cpf: str
    nome: str
    docto: str
    vencimento: date
    valor: float
    pago: bool
    data_pagto: Optional[date] = None
    tipo: str = "receber"


@dataclass
class Despesa:
    data: date
    razao_social: str
    descricao: str
    valor: float
    conta_debito: Optional[str] = None
    conta_credito: Optional[str] = None
    # Campos opcionais, usados pelo aprendizado_despesas.py quando uma
    # regra extra tem confiança/aviso/descrição próprios (ex: PRO LABORE
    # tem texto fixo, BELA KASA é "às vezes", não sempre) — quando não
    # vêm preenchidos, o motor usa o padrão de sempre (confiança "alta",
    # descrição "Pg. ref. {razao_social} - {descricao}").
    confianca: Optional[str] = None
    aviso: str = ""
    descricao_override: Optional[str] = None


@dataclass
class NotaServico:
    data: date
    numero: str
    cnpj_cpf: str
    razao_social: str
    valor: float
    iss: float = 0.0
    cancelada: bool = False


@dataclass
class Terceiro:
    codigo: str
    nome_truncado: str
    conta: str


@dataclass
class DespesaJaLancada:
    data: date
    valor: float
    tipo: str
    historico: str
    conta_parceira: str = ""
    terceiro: str = ""


@dataclass
class LancamentoClassificado:
    data: date
    descricao: str
    valor: float
    tipo: str
    conta_debito: str = ""
    conta_credito: str = ""
    terceiro_debito: str = ""
    terceiro_credito: str = ""
    origem: str = "simples"
    confianca: str = "baixa"
    casada: bool = False
    aviso: str = ""
    referencia: str = ""