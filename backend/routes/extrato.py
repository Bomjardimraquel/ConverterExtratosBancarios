from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from rq.job import Job
from rq.exceptions import NoSuchJobError

from parsers.factory import get_parser  # mantido: usado para validar o parser antes de enfileirar
from tasks import processar_extrato_job
from utils.fila import conexao_redis, fila_processamento
from utils.exportar_excel import gerar_excel
from utils.contas import CONTAS, BANCO_CONTA
from pydantic import BaseModel
from typing import List, Optional
import io

router = APIRouter()


# ── Listar bancos e contas disponíveis ──────────────────────────────────────
@router.get("/bancos")
def listar_bancos():
    bancos = [
        {"key": "bb", "nome": "Banco do Brasil", "conta": "11041"},
        {"key": "emprestimo_bb", "nome": "Empréstimo BB", "conta": "21381"},
        {"key": "sicoob", "nome": "Sicoob", "conta": "11120"},
        {"key": "sicoob_aplic", "nome": "Sicoob Aplicação", "conta": "11161"},
        {"key": "emprestimo_sicoob", "nome": "Empréstimo Sicoob", "conta": "21325"},
        {"key": "itau", "nome": "Itaú", "conta": "11045"},
        {"key": "pagbank", "nome": "PagBank", "conta": "11127"},
        {"key": "santander", "nome": "Santander", "conta": "11126"},
        {"key": "bradesco", "nome": "Bradesco", "conta": "11044"},
        {"key": "nordeste", "nome": "Banco do Nordeste", "conta": "11042"},
    ]
    return {"bancos": bancos, "contas": CONTAS}


# ── Upload: agora só enfileira o job e devolve na hora ──────────────────────
@router.post("/processar")
async def processar_extrato(
    arquivo: UploadFile = File(...),
    banco: str = Form(...),
    nome_empresa: str = Form(""),
    mes_ano: str = Form(""),
):
    if not arquivo.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são suportados.")

    conteudo = await arquivo.read()
    if len(conteudo) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    conta_banco = BANCO_CONTA.get(banco)
    if not conta_banco:
        raise HTTPException(status_code=400, detail=f"Banco '{banco}' não reconhecido.")

    # Validação rápida: garante que existe parser pra esse banco ANTES de
    # enfileirar. Erros de "banco não suportado" continuam respondendo na
    # hora (400), sem precisar esperar o worker pra descobrir isso.
    try:
        get_parser(banco, conta_banco)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parser inválido para o banco '{banco}': {str(e)}")

    job = fila_processamento.enqueue(
        processar_extrato_job,
        conteudo,
        banco,
        conta_banco,
        nome_empresa,
        mes_ano,
        job_timeout="10m",  # ajuste conforme o tamanho esperado dos PDFs (OCR pode precisar de mais)
    )

    return {"job_id": job.id, "status": "processando"}


# ── Consulta de status do job ───────────────────────────────────────────────
@router.get("/status/{job_id}")
def consultar_status(job_id: str):
    try:
        job = Job.fetch(job_id, connection=conexao_redis)
    except NoSuchJobError:
        raise HTTPException(status_code=404, detail="Job não encontrado.")

    if job.is_finished:
        return {"status": "concluido", "resultado": job.result}

    if job.is_failed:
        # job.exc_info tem o traceback completo (útil pra você debugar);
        # devolvemos só a última linha pro usuário final não ver isso tudo.
        erro_resumido = (job.exc_info or "Erro desconhecido").strip().splitlines()[-1]
        return {"status": "erro", "erro": erro_resumido}

    # queued (na fila, ainda não começou) ou started (rodando agora)
    return {"status": "processando"}


# ── Exportar Excel com lançamentos (possivelmente editados) ─────────────────
class LancamentoIn(BaseModel):
    data: str
    descricao: str
    tipo: str
    conta_debito: str
    conta_credito: str
    valor: float
    classificacao: Optional[str] = ""
    requer_revisao: Optional[bool] = False


class ExportarRequest(BaseModel):
    lancamentos: List[LancamentoIn]
    banco: str = ""
    nome_empresa: str = ""
    mes_ano: str = ""


@router.post("/exportar")
def exportar_excel(payload: ExportarRequest):
    if not payload.lancamentos:
        raise HTTPException(status_code=400, detail="Nenhum lançamento para exportar.")

    dados = [l.model_dump() for l in payload.lancamentos]
    excel_bytes = gerar_excel(dados, payload.nome_empresa, payload.banco, payload.mes_ano)

    partes = [p for p in [payload.nome_empresa, payload.mes_ano] if p]
    nome_arquivo = ("_".join(partes) if partes else f"lancamentos_{payload.banco}").replace(" ", "_") + ".xlsx"

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )