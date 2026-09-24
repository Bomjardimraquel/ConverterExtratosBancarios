"""
Job de processamento do Módulo 3: lê o razão enviado, roda o
MotorAnaliseRazao e monta o resultado — mesmo padrão de
modulo2/tasks_modulo2.py (roda dentro do worker, não do backend).
"""
import base64
import os
import tempfile

from dotenv import load_dotenv

_CAMINHO_ENV = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(os.path.normpath(_CAMINHO_ENV))

try:
    from .parser_razao import parse_razao, parse_metadados, RazaoParseError
    from .motor_analise import analisar
    from .gerar_excel_achados import gerar_excel_achados
except ImportError:
    from parser_razao import parse_razao, parse_metadados, RazaoParseError
    from motor_analise import analisar
    from gerar_excel_achados import gerar_excel_achados


def _achado_para_dict(a) -> dict:
    return {
        "grupo": a.grupo, "acesso": a.acesso, "nome_conta": a.nome_conta,
        "terceiro": a.terceiro, "tipo": a.tipo, "descricao": a.descricao,
        "severidade": a.severidade, "valor": a.valor, "referencia": a.referencia,
    }


def processar_razao_job(
    empresa_id: str,
    grupo: str,
    arquivo_razao_conteudo: bytes,
) -> dict:
    """
    empresa_id: código da empresa (ex: "A25"), só usado como rótulo no
        resultado; a análise em si não depende de config nenhuma dela.
    grupo: "ativo" | "passivo" | "despesas" | "receitas", o grupo que a
        pessoa escolheu na tela, guardado só pra exibir no resultado. O
        motor analisa TODOS os blocos que encontrar no arquivo, não filtra
        por acesso específico (ver parser_razao.py).
    """
    with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as tmp:
        tmp.write(arquivo_razao_conteudo)
        caminho = tmp.name

    try:
        metadados = parse_metadados(caminho)
        blocos = parse_razao(caminho)
    except RazaoParseError as e:
        raise ValueError(str(e))
    finally:
        os.unlink(caminho)

    achados = analisar(blocos, data_referencia=metadados.get("data_emissao"))
    total_lancamentos = sum(len(b.lancamentos) for b in blocos)

    excel_bytes = gerar_excel_achados(
        achados, nome_empresa=metadados.get("empresa") or empresa_id,
        periodo=metadados.get("periodo"),
    )
    nome_arquivo = f"analise_{empresa_id}_{grupo}.xlsx"

    return {
        "empresa_id": empresa_id,
        "nome_empresa": metadados.get("empresa") or empresa_id,
        "grupo": grupo,
        "total_contas": len(blocos),
        "total_lancamentos": total_lancamentos,
        "achados": [_achado_para_dict(a) for a in achados],
        "arquivo": nome_arquivo,
        "arquivo_base64": base64.b64encode(excel_bytes).decode("ascii"),
    }