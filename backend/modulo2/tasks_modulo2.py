"""
Job de processamento completo do Módulo 2: pega o extrato (Módulo 1),
o relatório de títulos e o arquivo de despesa classificada/razão do
Prosoft, roda o MotorCruzamento e gera o Excel final.

Fica separado do tasks.py do Módulo 1 de propósito — são pipelines
diferentes (esse aqui tem mais etapas e demora mais), mas os dois usam
a mesma fila do Redis (fila_processamento), então não precisa de
infraestrutura nova.
"""
import os
import json

from parsers.factory import get_parser
from modulo2.cruzamento import MotorCruzamento
from modulo2.carregador_despesas import carregar_arquivo_despesas_ou_razao
from modulo2.carregar_titulos import carregar_titulos
from modulo2.adaptador_lancamentos import converter_lancamentos_base
from modulo2.gerar_excel_final import gerar_excel_final

CAMINHO_EMPRESAS_JSON = os.path.join(os.path.dirname(__file__), "config", "empresas.json")
PASTA_SAIDA = os.path.join(os.path.dirname(__file__), "..", "arquivos_gerados")


def _carregar_config_empresa(empresa: str) -> dict:
    # encoding="utf-8" explícito — sem isso, no Windows o Python tenta ler
    # com cp1252 por padrão e quebra em qualquer acento do arquivo.
    with open(CAMINHO_EMPRESAS_JSON, encoding="utf-8") as f:
        empresas = json.load(f)
    cfg = empresas.get(empresa)
    if not cfg:
        raise ValueError(
            f"Empresa '{empresa}' não encontrada em empresas.json. "
            f"Empresas disponíveis: {sorted(empresas.keys())}"
        )
    return cfg


def processar_completo_job(
    empresa: str,
    banco: str,
    ano: int,
    extrato_conteudo: bytes,
    titulos_conteudo: bytes,
    tipo_titulos: str,
    despesas_conteudo: bytes,
    nome_empresa: str = "",
    mes_ano: str = "",
) -> dict:
    """
    empresa: código da empresa no empresas.json (ex: "D08")
    banco: chave do banco (ex: "bb", "sicoob", "itau") — precisa bater
           com uma das chaves em cfg["bancos"] dessa empresa
    ano: ano do extrato (o parser do Módulo 1 só devolve "DD/MM", sem ano)
    tipo_titulos: "receber" ou "pagar"
    """
    cfg = _carregar_config_empresa(empresa)

    bancos_cfg = cfg.get("bancos", {})
    conta_banco = bancos_cfg.get(banco)
    if not conta_banco:
        raise ValueError(
            f"Banco '{banco}' não configurado para a empresa '{empresa}'. "
            f"Bancos disponíveis pra ela: {list(bancos_cfg.keys())}"
        )

    # 1. Extrato — mesmo parser do Módulo 1, já corrigido
    parser = get_parser(banco, conta_banco)
    lancamentos_base = parser.parse(extrato_conteudo)
    if not lancamentos_base:
        raise ValueError(
            "Nenhum lançamento encontrado no extrato. Confirma se o banco "
            "selecionado bate com o extrato enviado."
        )
    lancamentos = converter_lancamentos_base(lancamentos_base, ano=ano)

    # 2. Relatório de títulos
    titulos = carregar_titulos(titulos_conteudo, tipo=tipo_titulos)

    # 3. Despesa classificada OU razão do Prosoft — detecção automática
    #    pela estrutura do arquivo (não precisa mais de modo_despesas na config)
    modo, dados_despesa = carregar_arquivo_despesas_ou_razao(despesas_conteudo)
    kwargs_motor = (
        {"despesas": dados_despesa} if modo == "despesa_classificada"
        else {"despesas_ja_lancadas": dados_despesa}
    )

    # 4. Cruzamento
    motor = MotorCruzamento(cfg, conta_banco=conta_banco)
    resultado = motor.cruzar(lancamentos, titulos=titulos, modo_despesas=modo, **kwargs_motor)

    # 5. Excel final
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    nome_arquivo = f"{empresa}_{banco}_{mes_ano.replace('/', '-') or 'sem-data'}.xlsx".replace(" ", "_")
    caminho_arquivo = os.path.join(PASTA_SAIDA, nome_arquivo)
    titulo_planilha = f"{nome_empresa or cfg.get('nome', empresa)} - {mes_ano}"
    stats = gerar_excel_final(motor, resultado, titulo_planilha, caminho_arquivo)

    casados = sum(1 for r in resultado if r.casada)
    valor_total = sum(r.valor for r in resultado)
    valor_casado = sum(r.valor for r in resultado if r.casada)

    return {
        "empresa": empresa,
        "nome_empresa": cfg.get("nome", empresa),
        "banco": banco,
        "total_lancamentos": len(lancamentos),
        "casados": casados,
        "percentual_casado": round(100 * valor_casado / valor_total, 1) if valor_total else 0,
        "linhas_excel": stats["linhas_lancamentos"],
        "linhas_pendencias": stats["linhas_pendencias"],
        "arquivo": nome_arquivo,
    }