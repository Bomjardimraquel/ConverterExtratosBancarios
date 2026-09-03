from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from rq.job import Job
from rq.exceptions import NoSuchJobError

from modulo2.db.carregar_config import listar_empresas
from utils.fila import conexao_redis, fila_processamento

router = APIRouter()


@router.get("/empresas")
def get_empresas():
    """Lista as empresas cadastradas (código, nome, bancos configurados)
    — usada pelo front pra montar os selects da tela de upload."""
    return {"empresas": listar_empresas()}


@router.post("/processar_completo")
async def processar_completo(
    empresa: str = Form(...),
    banco: str = Form(...),
    mes_ano: str = Form(...),        # formato "MM/AAAA", ex: "04/2026"
    tipo_titulos: str = Form("receber"),  # "receber" ou "pagar"
    nome_empresa: str = Form(""),
    extrato: UploadFile = File(...),
    arquivo_titulos: UploadFile = File(None),
    arquivo_despesas: UploadFile = File(None),
    arquivo_razao: UploadFile = File(None),
    arquivo_modelo_classificado: UploadFile = File(None),
):
    """
    Recebe o extrato (PDF do banco) — o único arquivo realmente
    obrigatório — e, opcionalmente, qualquer combinação de:
      - arquivo_titulos: relatório de títulos (.xls)
      - arquivo_despesas: despesa já classificada (Débito/Crédito
        preenchidos) OU movimento bruto (cru, com Favorecido, sem
        Débito/Crédito) — detecção automática entre os dois formatos.
        Quando for movimento bruto, usa as regras_texto/regras_extras já
        salvas na config da empresa (o aprendizado virou permanente).
        `arquivo_modelo_classificado` é OPCIONAL: só precisa mandar se
        quiser ENSINAR fornecedor novo que as regras salvas ainda não
        reconhecem (um mês já classificado, usado como "gabarito" só
        pra essa rodada).
      - arquivo_razao: razão do Prosoft (SpreadsheetML) — cobre o que já
        foi lançado no Prosoft.
    Sem título/despesa/razão, o lançamento simplesmente não acha
    correspondência e cai na classificação comum (regra de texto ou
    banco x caixa) — permite conciliar com o que a pessoa já tiver na
    hora, sem exigir todos os arquivos de uma vez.
    Enfileira o job que roda o MotorCruzamento e gera o Excel final.
    """
    if tipo_titulos not in ("receber", "pagar"):
        raise HTTPException(400, "tipo_titulos precisa ser 'receber' ou 'pagar'.")

    try:
        _, ano_str = mes_ano.split("/")
        ano = int(ano_str)
    except ValueError:
        raise HTTPException(400, "mes_ano precisa estar no formato MM/AAAA, ex: '04/2026'.")

    extrato_conteudo = await extrato.read()
    titulos_conteudo = await arquivo_titulos.read() if arquivo_titulos else None
    despesas_conteudo = await arquivo_despesas.read() if arquivo_despesas else None
    razao_conteudo = await arquivo_razao.read() if arquivo_razao else None
    modelo_conteudo = await arquivo_modelo_classificado.read() if arquivo_modelo_classificado else None

    if not extrato_conteudo:
        raise HTTPException(400, "Extrato veio vazio.")

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
        extrato_conteudo, titulos_conteudo, tipo_titulos,
        despesas_conteudo, razao_conteudo,
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


@router.get("/download/{job_id}")
def baixar_excel(job_id: str):
    """
    Lê o arquivo do RESULTADO DO JOB (Redis), não mais do disco local —
    worker e backend rodam em serviços separados no Railway, cada um com
    disco próprio, então salvar só o caminho não bastava (o backend nunca
    via o arquivo que o worker tinha gerado no disco DELE).
    """
    import base64
    from fastapi import Response

    try:
        job = Job.fetch(job_id, connection=conexao_redis)
    except NoSuchJobError:
        raise HTTPException(404, "Job não encontrado (talvez o resultado já tenha expirado).")

    if not job.is_finished or not job.result:
        raise HTTPException(404, "Arquivo não encontrado (talvez ainda esteja processando).")

    arquivo_base64 = job.result.get("arquivo_base64")
    nome_arquivo = job.result.get("arquivo", "resultado.xlsx")
    if not arquivo_base64:
        raise HTTPException(404, "Arquivo não encontrado no resultado do processamento.")

    conteudo = base64.b64decode(arquivo_base64)
    return Response(
        content=conteudo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )