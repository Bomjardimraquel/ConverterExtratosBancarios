"""
Carrega a config de uma empresa a partir do Postgres, remontando o MESMO
formato de dict que o resto do sistema (MotorCruzamento, aprendizado_
despesas.py, tasks_modulo2.py) já espera — igualzinho ao que
json.load(empresas.json)["A25"] já dava. Nenhum desses arquivos precisa
mudar uma linha: só essa função troca de onde vem o dado.
"""
from sqlmodel import Session, select

from .conexao import engine
from .tabelas import Empresa, EmpresaRegra, EmpresaRegraTermo


def listar_empresas() -> list:
    """
    Lista resumida de todas as empresas — só o suficiente pro front
    montar os selects (código, nome, quais bancos essa empresa usa).
    Não remonta a config inteira (regras, terceiros etc), que é bem mais
    pesado e só faz sentido na hora de processar de verdade.
    """
    with Session(engine) as session:
        empresas = session.exec(select(Empresa).order_by(Empresa.id)).all()
        return [
            {
                "id": e.id,
                "nome": e.nome,
                "bancos": [{"key": b.banco_key, "conta": b.conta_banco} for b in e.bancos],
            }
            for e in empresas
        ]


def _regra_para_dict(regra: EmpresaRegra, session: Session) -> dict:
    termos_stmt = select(EmpresaRegraTermo).where(EmpresaRegraTermo.regra_id == regra.id)
    termos = session.exec(termos_stmt).all()

    termos_contem = [t.termo for t in termos if t.tipo != "nao_contem"]
    termos_nao_contem = [t.termo for t in termos if t.tipo == "nao_contem"]

    d = {}
    if regra.modo_match == "contem_todos":
        d["contem_todos"] = termos_contem
    else:
        d["contem"] = termos_contem
    if termos_nao_contem:
        d["nao_contem"] = termos_nao_contem

    if regra.usa_padrao:
        d["usa_padrao"] = True
    if regra.descricao_template:
        d["descricao_template"] = regra.descricao_template
    if regra.descricao_sem_nome:
        d["descricao_sem_nome"] = regra.descricao_sem_nome
    if regra.descricao_dinamica:
        d["descricao_dinamica"] = True
    if regra.descricao:
        d["descricao"] = regra.descricao
    if regra.confianca != "media":
        d["confianca"] = regra.confianca
    if regra.aviso:
        d["aviso"] = regra.aviso

    # nome do campo de conta muda dependendo do contexto — bate com o
    # que regras_texto (debito_D/credito_C) e regras_extras
    # (conta_debito) já esperavam no JSON
    # nome do campo de conta muda dependendo do contexto — bate com o
    # que regras_texto (debito_D/credito_C) e regras_extras
    # (conta_debito) já esperavam no JSON. "aviso_simples" não define
    # conta nenhuma de propósito — só serve pra trocar o texto do aviso
    # de um lançamento que continua caindo na classificação comum.
    if regra.contexto == "extrato":
        if regra.conta_debito:
            d["debito_D"] = regra.conta_debito
        if regra.conta_credito:
            d["credito_C"] = regra.conta_credito
    elif regra.contexto == "despesa_bruta":
        if regra.conta_debito:
            d["conta_debito"] = regra.conta_debito
    # contexto == "aviso_simples": não faz nada aqui, só usa contem/aviso
    # (já preenchidos acima)

    return d


def carregar_config_empresa(empresa_id: str) -> dict:
    with Session(engine) as session:
        empresa = session.get(Empresa, empresa_id)
        if not empresa:
            raise ValueError(f"Empresa '{empresa_id}' não encontrada no banco.")

        cfg = {
            "nome": empresa.nome,
            "cnpj": empresa.cnpj,
            "grupo": empresa.grupo,
            "regime": empresa.regime,
            "conta_caixa": empresa.conta_caixa,
            "conta_clientes": empresa.conta_clientes,
            "conta_fornecedores": empresa.conta_fornecedores,
            "casa_pf": empresa.casa_pf,
            "cruzamento": {
                "tolerancia_valor": empresa.tolerancia_valor,
                "janela_dias_despesa": empresa.janela_dias_despesa,
                "janela_dias_titulo_pj": empresa.janela_dias_titulo_pj,
            },
            "bancos": {b.banco_key: b.conta_banco for b in empresa.bancos},
            "terceiros_clientes": {t.nome: t.codigo for t in empresa.terceiros if t.tipo == "cliente"},
            "terceiros_fornecedores": {t.nome: t.codigo for t in empresa.terceiros if t.tipo == "fornecedor"},
        }

        if empresa.conta_aplicacao:
            cfg["conta_aplicacao"] = empresa.conta_aplicacao
        if empresa.conta_saida_sem_match:
            cfg["conta_saida_sem_match"] = empresa.conta_saida_sem_match

        if empresa.intermediarios:
            cfg["intermediarios_financeiros"] = [i.nome for i in empresa.intermediarios]
        if empresa.ignorar_despesas:
            cfg["ignorar_se_contem"] = [i.termo for i in empresa.ignorar_despesas]

        regras_extrato = sorted([r for r in empresa.regras if r.contexto == "extrato"], key=lambda r: r.ordem)
        regras_despesa = sorted([r for r in empresa.regras if r.contexto == "despesa_bruta"], key=lambda r: r.ordem)
        regras_aviso = sorted([r for r in empresa.regras if r.contexto == "aviso_simples"], key=lambda r: r.ordem)

        if regras_extrato:
            cfg["regras_texto"] = [_regra_para_dict(r, session) for r in regras_extrato]
        if regras_despesa:
            cfg["regras_extras"] = [_regra_para_dict(r, session) for r in regras_despesa]
        if regras_aviso:
            cfg["avisos_personalizados"] = [_regra_para_dict(r, session) for r in regras_aviso]

        return cfg