from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from parsers.factory import get_parser
from utils.exportar_excel import gerar_excel
from utils.contas import CONTAS, BANCO_CONTA
from pydantic import BaseModel
from typing import List, Optional
import io
import json

router = APIRouter()


# ── Listar bancos e contas disponíveis ──────────────────────────────────────
@router.get("/bancos")
def listar_bancos():
    bancos = [
        {"key": "bb", "nome": "Banco do Brasil", "conta": "11041"},
        {"key": "bb_rende_facil", "nome": "BB Rende Fácil (Aplicação)", "conta": "11142"},
        {"key": "emprestimo_bb", "nome": "Empréstimo BB", "conta": "21381"},
        {"key": "sicoob", "nome": "Sicoob", "conta": "11120"},
        {"key": "emprestimo_sicoob", "nome": "Empréstimo Sicoob", "conta": "21325"},
        {"key": "itau", "nome": "Itaú", "conta": "11045"},
        {"key": "itau_aplicacao", "nome": "Itaú (Aplicação)", "conta": "11146"},
        {"key": "pagbank", "nome": "PagBank", "conta": "11127"},
        {"key": "santander", "nome": "Santander", "conta": "11126"},
        {"key": "bradesco", "nome": "Bradesco", "conta": "11044"},
        {"key": "nordeste", "nome": "Banco do Nordeste", "conta": "11042"},
    ]
    return {"bancos": bancos, "contas": CONTAS}


# ── Upload e processamento do extrato ───────────────────────────────────────
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

    try:
        parser = get_parser(banco, conta_banco)
        lancamentos = parser.parse(conteudo)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar PDF: {str(e)}")

    if not lancamentos:
        raise HTTPException(
            status_code=422,
            detail="Nenhum lançamento encontrado no PDF. Verifique se o banco selecionado está correto."
        )

    return {
        "total": len(lancamentos),
        "banco": banco,
        "nome_empresa": nome_empresa,
        "mes_ano": mes_ano,
        "lancamentos": [l.to_dict() for l in lancamentos],
    }


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

    nome_arquivo = f"lancamentos_{payload.banco}_{payload.mes_ano or 'extrato'}.xlsx".replace(" ", "_")

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )
