"""
Migra o empresas.json que já existe pras tabelas do Postgres. Roda uma
vez só (ou de novo, se quiser recomeçar do zero — ele limpa antes de
inserir, pra não duplicar).

Uso:
    DATABASE_URL="postgresql://postgres:SENHA@localhost:5432/conciliador" \
        python -m modulo2.db.migrar_json_para_banco caminho/pro/empresas.json
"""
import sys
import json

from sqlmodel import SQLModel, Session, delete

from .conexao import engine
from .tabelas import (
    Empresa, EmpresaBanco, EmpresaTerceiro, EmpresaRegra,
    EmpresaRegraTermo, EmpresaIntermediario, EmpresaIgnorarDespesa,
)


def _migrar_regras(session: Session, empresa_id: str, lista_regras: list, contexto: str):
    for ordem, regra in enumerate(lista_regras):
        conta_debito = regra.get("debito_D") or regra.get("conta_debito")
        db_regra = EmpresaRegra(
            empresa_id=empresa_id,
            contexto=contexto,
            ordem=ordem,
            modo_match="contem_todos" if regra.get("contem_todos") else "contem",
            conta_debito=conta_debito,
            conta_credito=regra.get("credito_C"),
            usa_padrao=regra.get("usa_padrao", False),
            descricao=regra.get("descricao"),
            descricao_template=regra.get("descricao_template"),
            descricao_sem_nome=regra.get("descricao_sem_nome"),
            descricao_dinamica=regra.get("descricao_dinamica", False),
            confianca=regra.get("confianca", "media"),
            aviso=regra.get("aviso", ""),
        )
        session.add(db_regra)
        session.flush()  # pra já ter o db_regra.id antes de criar os termos

        termos = regra.get("contem_todos") or regra.get("contem") or []
        tipo_termo = "contem_todos" if regra.get("contem_todos") else "contem"
        for termo in termos:
            session.add(EmpresaRegraTermo(regra_id=db_regra.id, termo=termo, tipo=tipo_termo))
        for termo in regra.get("nao_contem", []):
            session.add(EmpresaRegraTermo(regra_id=db_regra.id, termo=termo, tipo="nao_contem"))


def migrar(caminho_json: str, limpar_antes: bool = True):
    with open(caminho_json, encoding="utf-8") as f:
        empresas_json = json.load(f)

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        if limpar_antes:
            # limpa tudo antes de inserir de novo, pra rodar o script
            # quantas vezes precisar sem duplicar
            for tabela in (EmpresaRegraTermo, EmpresaRegra, EmpresaTerceiro,
                           EmpresaBanco, EmpresaIntermediario, EmpresaIgnorarDespesa, Empresa):
                session.exec(delete(tabela))
            session.commit()

        for empresa_id, dados in empresas_json.items():
            cruzamento = dados.get("cruzamento", {})
            empresa = Empresa(
                id=empresa_id,
                nome=dados.get("nome", empresa_id),
                cnpj=dados.get("cnpj"),
                grupo=dados.get("grupo", ""),
                regime=dados.get("regime", ""),
                conta_caixa=dados.get("conta_caixa", "11002"),
                conta_clientes=dados.get("conta_clientes", "11401"),
                conta_fornecedores=dados.get("conta_fornecedores", "28625"),
                conta_aplicacao=dados.get("conta_aplicacao"),
                conta_saida_sem_match=dados.get("conta_saida_sem_match"),
                casa_pf=dados.get("casa_pf", False),
                tolerancia_valor=cruzamento.get("tolerancia_valor", 0.02),
                janela_dias_despesa=cruzamento.get("janela_dias_despesa", 3),
                janela_dias_titulo_pj=cruzamento.get("janela_dias_titulo_pj", 30),
            )
            session.add(empresa)

            for banco_key, conta_banco in dados.get("bancos", {}).items():
                session.add(EmpresaBanco(empresa_id=empresa_id, banco_key=banco_key, conta_banco=conta_banco))

            for nome, codigo in dados.get("terceiros_clientes", {}).items():
                session.add(EmpresaTerceiro(empresa_id=empresa_id, tipo="cliente", nome=nome, codigo=codigo))
            for nome, codigo in dados.get("terceiros_fornecedores", {}).items():
                session.add(EmpresaTerceiro(empresa_id=empresa_id, tipo="fornecedor", nome=nome, codigo=codigo))

            for nome in dados.get("intermediarios_financeiros", []):
                session.add(EmpresaIntermediario(empresa_id=empresa_id, nome=nome))

            for termo in dados.get("ignorar_se_contem", []):
                session.add(EmpresaIgnorarDespesa(empresa_id=empresa_id, termo=termo))

            _migrar_regras(session, empresa_id, dados.get("regras_texto", []), "extrato")
            _migrar_regras(session, empresa_id, dados.get("regras_extras", []), "despesa_bruta")

        session.commit()

    print(f"Migrado: {len(empresas_json)} empresas.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "config/empresas.json"
    migrar(caminho)