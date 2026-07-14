import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from rq.job import Job
from rq.exceptions import NoSuchJobError

from modulo2.tasks_modulo2 import PASTA_SAIDA
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
    arquivo_modelo_classificado: UploadFile = File(None),
):
    """
    Recebe extrato (PDF do banco) + relatório de títulos (.xls) +
    arquivo de despesas — detectado automaticamente entre 3 formatos:
      - despesa já classificada (Débito/Crédito preenchidos)
      - razão do Prosoft (SpreadsheetML)
      - movimento bruto (cru, com Favorecido, sem Débito/Crédito) —
        classificado usando as regras_texto/regras_extras já salvas na
        config da empresa (o aprendizado virou permanente, igual as
        regras do extrato). `arquivo_modelo_classificado` é OPCIONAL
        aqui: só precisa mandar se quiser ENSINAR fornecedor novo que
        as regras salvas ainda não reconhecem (um mês já classificado,
        usado como "gabarito" só pra essa rodada).
    e enfileira o job que roda o MotorCruzamento e gera o Excel final.
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
    modelo_conteudo = await arquivo_modelo_classificado.read() if arquivo_modelo_classificado else None

    if not extrato_conteudo:
        raise HTTPException(400, "Extrato veio vazio.")
    if not titulos_conteudo:
        raise HTTPException(400, "Arquivo de títulos veio vazio.")
    if not despesas_conteudo:
        raise HTTPException(400, "Arquivo de despesa/razão veio vazio.")

    # Passa o caminho da função como STRING explícita ("modulo2.tasks_modulo2.
    # processar_completo_job"), em vez de passar o objeto função direto.
    # Motivo: passando o objeto, o RQ tenta montar esse mesmo caminho
    # sozinho (lendo func.__module__), e com a função dentro de uma
    # subpasta (modulo2/) isso saiu errado — o Redis guardava só
    # "processar_completo_job", sem o caminho da pasta na frente, e o
    # worker (processo separado) não achava a função na hora de rodar.
    # Escrevendo o caminho na mão, elimina essa ambiguidade de vez.
    job = fila_processamento.enqueue(
        "modulo2.tasks_modulo2.processar_completo_job",
        empresa, banco, ano,
        extrato_conteudo, titulos_conteudo, tipo_titulos, despesas_conteudo,
        nome_empresa, mes_ano, modelo_conteudo,
        job_timeout="15m",
        result_ttl=3600,  # 1h pra consultar o resultado, em vez dos 500s padrão
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