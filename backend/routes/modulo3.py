from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response
from rq.job import Job
from rq.exceptions import NoSuchJobError
import base64

from modulo2.db.carregar_config import listar_empresas
from modulo3.acessos_sugeridos import sugerir_acessos
from utils.fila import conexao_redis, fila_processamento

router = APIRouter()

GRUPOS_VALIDOS = ("ativo", "passivo", "despesas", "receitas")


@router.get("/empresas")
def get_empresas():
    """Mesma lista do Módulo 2, mas essa é a tela que realmente usa
    grupo/regime — é por causa deles que listar_empresas() passou a
    devolver os dois."""
    return {"empresas": listar_empresas()}


@router.get("/acessos/{empresa_id}")
def get_acessos_sugeridos(empresa_id: str, grupo: str):
    if grupo not in GRUPOS_VALIDOS:
        raise HTTPException(400, f"grupo precisa ser um de {GRUPOS_VALIDOS}.")

    empresa = next((e for e in listar_empresas() if e["id"] == empresa_id), None)
    if not empresa:
        raise HTTPException(404, f"Empresa '{empresa_id}' não encontrada.")

    return {"acessos": sugerir_acessos(empresa, grupo)}


@router.post("/processar")
async def processar(
    empresa: str = Form(...),
    grupo: str = Form(...),
    arquivo_razao: UploadFile = File(...),
):
    """
    Enfileira a análise do razão enviado. O motor processa todo bloco
    "Conta:" que encontrar no arquivo (ver modulo3/parser_razao.py); o
    "grupo" aqui é só pra rotular/organizar o resultado (Ativo, Passivo,
    Despesas ou Receitas) - a gente pode voltar a pedir o Acesso
    específico quando tiver regras que dependam de conta a conta (ver
    modulo3/acessos_sugeridos.py, hoje não usado por aqui).
    """
    if grupo not in GRUPOS_VALIDOS:
        raise HTTPException(400, f"grupo precisa ser um de {GRUPOS_VALIDOS}.")

    conteudo = await arquivo_razao.read()
    if not conteudo:
        raise HTTPException(400, "Arquivo de razão veio vazio.")

    job = fila_processamento.enqueue(
        "modulo3.tasks_modulo3.processar_razao_job",
        empresa, grupo, conteudo,
        job_timeout="10m",
        result_ttl=3600,
    )
    return {"job_id": job.id, "status": "processando"}


@router.get("/status/{job_id}")
def consultar_status(job_id: str):
    try:
        job = Job.fetch(job_id, connection=conexao_redis)
    except NoSuchJobError:
        raise HTTPException(404, "Job não encontrado.")

    if job.is_finished:
        # não manda o base64 do Excel de volta no polling — só quando
        # a pessoa realmente clicar em baixar (endpoint /download abaixo)
        resultado = {k: v for k, v in job.result.items() if k != "arquivo_base64"}
        return {"status": "concluido", "resultado": resultado}

    if job.is_failed:
        erro_resumido = (job.exc_info or "Erro desconhecido").strip().splitlines()[-1]
        return {"status": "erro", "erro": erro_resumido}

    return {"status": "processando"}


@router.get("/download/{job_id}")
def baixar_excel(job_id: str):
    try:
        job = Job.fetch(job_id, connection=conexao_redis)
    except NoSuchJobError:
        raise HTTPException(404, "Job não encontrado (talvez o resultado já tenha expirado).")

    if not job.is_finished or not job.result:
        raise HTTPException(404, "Arquivo não encontrado (talvez ainda esteja processando).")

    arquivo_base64 = job.result.get("arquivo_base64")
    nome_arquivo = job.result.get("arquivo", "analise.xlsx")
    if not arquivo_base64:
        raise HTTPException(404, "Arquivo não encontrado no resultado do processamento.")

    conteudo = base64.b64decode(arquivo_base64)
    return Response(
        content=conteudo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )