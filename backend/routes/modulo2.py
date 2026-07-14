import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from rq.job import Job
from rq.exceptions import NoSuchJobError

from modulo2.tasks_modulo2 import processar_completo_job, PASTA_SAIDA
from utils.fila import conexao_redis, fila_processamento

router = APIRouter()


@router.post("/processar_completo")
async def processar_completo(
    empresa: str = Form(...),
    banco: str = Form(...),
    mes_ano: str = Form(...),        # formato "MM/AAAA", ex: "04/2026"
    tipo_titulos: str = Form("receber"),  # "receber" ou "pagar"
    nome_empresa: str = Form(""),
    extrato: UploadFile = File(...),
    arquivo_titulos: UploadFile = File(...),
    arquivo_despesas_ou_razao: UploadFile = File(...),
):
    """
    Recebe extrato (PDF do banco) + relatório de títulos (.xls) +
    despesa classificada OU razão do Prosoft (detectado automaticamente
    pela estrutura do arquivo — não precisa dizer qual é qual) e enfileira
    o job que roda o MotorCruzamento e gera o Excel final.
    """
    if tipo_titulos not in ("receber", "pagar"):
        raise HTTPException(400, "tipo_titulos precisa ser 'receber' ou 'pagar'.")

    try:
        _, ano_str = mes_ano.split("/")
        ano = int(ano_str)
    except ValueError:
        raise HTTPException(400, "mes_ano precisa estar no formato MM/AAAA, ex: '04/2026'.")

    extrato_conteudo = await extrato.read()
    titulos_conteudo = await arquivo_titulos.read()
    despesas_conteudo = await arquivo_despesas_ou_razao.read()

    if not extrato_conteudo:
        raise HTTPException(400, "Extrato veio vazio.")
    if not titulos_conteudo:
        raise HTTPException(400, "Arquivo de títulos veio vazio.")
    if not despesas_conteudo:
        raise HTTPException(400, "Arquivo de despesa/razão veio vazio.")

    job = fila_processamento.enqueue(
        processar_completo_job,
        empresa, banco, ano,
        extrato_conteudo, titulos_conteudo, tipo_titulos, despesas_conteudo,
        nome_empresa, mes_ano,
        job_timeout="10m",
    )
    return {"job_id": job.id, "status": "processando"}


@router.get("/status_completo/{job_id}")
def consultar_status_completo(job_id: str):
    try:
        job = Job.fetch(job_id, connection=conexao_redis)
    except NoSuchJobError:
        raise HTTPException(404, "Job não encontrado.")

    if job.is_finished:
        return {"status": "concluido", "resultado": job.result}

    if job.is_failed:
        erro_resumido = (job.exc_info or "Erro desconhecido").strip().splitlines()[-1]
        return {"status": "erro", "erro": erro_resumido}

    return {"status": "processando"}


@router.get("/download/{nome_arquivo}")
def baixar_excel(nome_arquivo: str):
    # os.path.basename tira qualquer "../" que venha no nome — evita
    # alguém pedir um arquivo fora da pasta de saída pela URL.
    nome_seguro = os.path.basename(nome_arquivo)
    caminho = os.path.join(PASTA_SAIDA, nome_seguro)
    if not os.path.isfile(caminho):
        raise HTTPException(404, "Arquivo não encontrado (talvez ainda esteja processando).")
    return FileResponse(
        caminho,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=nome_seguro,
    )