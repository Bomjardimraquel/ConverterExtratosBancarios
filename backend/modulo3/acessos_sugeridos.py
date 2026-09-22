# Contas que aparecem em toda empresa, independente de regime ou modelo de
# negócio — confirmado comparando A25 e D08 nesta sessão.
ACESSOS_COMUNS = {
    "ativo": [
        {"codigo": "11002", "nome": "Caixa"},
        {"codigo": "11041", "nome": "Bco.do Brasil S/A.- 1"},
    ],
    "passivo": [
        {"codigo": "21401", "nome": "INSS a Recolher"},
        {"codigo": "21404", "nome": "FGTS a Recolher"},
        {"codigo": "21416", "nome": "Taxa Assistencial"},
        {"codigo": "21702", "nome": "Folha de Pagto.Empregs.a Pagar"},
        {"codigo": "21718", "nome": "Rescisoes Empgs.a Pagar"},
        {"codigo": "21727", "nome": "Pro-Labore a Pagar"},
        {"codigo": "21736", "nome": "Ferias empregs. a pagar"},
        {"codigo": "21759", "nome": "Unimed Extr Sul Coop Trab Méd"},
        {"codigo": "21788", "nome": "Empréstimo Consig. Trabalhador"},
        {"codigo": "21798", "nome": "Honorarios a Pagar"},
    ],
    "despesas": [
        {"codigo": "53003", "nome": "Ordenados"},
        {"codigo": "53007", "nome": "FGTS"},
        {"codigo": "53006", "nome": "Ferias"},
        {"codigo": "53009", "nome": "Rescisoes Cont.de Pessoal"},
        {"codigo": "53002", "nome": "Retirada Pro-Labore"},
        {"codigo": "53043", "nome": "Honorario Pessoa Juridica-Mtz."},
        {"codigo": "53053", "nome": "Aluguel"},
        {"codigo": "53164", "nome": "Assist.Médica/Odontologica"},
        {"codigo": "53502", "nome": "Despesas Bancarias"},
    ],
    "receitas": [],  # nada em comum entre os dois regimes na Receita, ver abaixo
}

# Só existem (ou só fazem sentido) num regime específico.
ACESSOS_POR_REGIME = {
    "lucro_presumido": {
        "ativo": [
            {"codigo": "11344", "nome": "I.R.R.F. Recuperar"},
            {"codigo": "11356", "nome": "Pis s/Fat.a Recuperar"},
            {"codigo": "11368", "nome": "COFINS Recuperar"},
            {"codigo": "11369", "nome": "CSLL Recuperar"},
        ],
        "passivo": [
            {"codigo": "21407", "nome": "Pis Receitas Oper.a Recolher"},
            {"codigo": "21408", "nome": "Cofins a Recolher"},
            {"codigo": "21505", "nome": "I.S.S. a Recolher"},
            {"codigo": "21504", "nome": "Imp.de Renda na Fonte a Recol."},
            {"codigo": "21501", "nome": "Prov.p/Pgto.Imp.de Renda"},
            {"codigo": "21502", "nome": "Contribuicao Social s/Lucros"},
            {"codigo": "21592", "nome": "Cofins/pis/csll fonte PJ/PJ"},
        ],
        "despesas": [
            {"codigo": "54101", "nome": "Prov.p/Pgto. Imp. de Renda"},
            {"codigo": "54102", "nome": "Contribuicao Social s/Lucros"},
        ],
        "receitas": [
            {"codigo": "63302", "nome": "(-) I.S.S."},
            {"codigo": "63303", "nome": "(-) Pis s/Faturamento"},
            {"codigo": "63304", "nome": "(-) Cofins"},
        ],
    },
    "simples": {
        "ativo": [],
        "passivo": [
            {"codigo": "21533", "nome": "Simples Nacional a Recolher"},
            {"codigo": "21527", "nome": "ICMS Antep.Tributaria a Rec."},
        ],
        "despesas": [
            {"codigo": "53426", "nome": "ICMS Antec.Tributaria"},
        ],
        "receitas": [
            {"codigo": "63105", "nome": "(-) Simples Nacional"},
        ],
    },
}

# Só existem (ou só fazem sentido) num modelo de negócio específico.
# conta_clientes/conta_fornecedores vêm do próprio registro da empresa
# (já existem em Empresa) — aqui só decide SE oferece o atalho, o código
# exato é lido do cadastro dela, não fixado aqui.
GRUPOS_POR_MODELO = {
    "servicos": {"ativo": "conta_clientes"},
    "comercio": {"passivo": "conta_fornecedores"},
}
NOMES_CONTA_MODELO = {
    "conta_clientes": "Clientes Diversos",
    "conta_fornecedores": "Fornecedores Diversos",
}


def sugerir_acessos(empresa: dict, grupo: str) -> list:
    """
    empresa: dict no formato que listar_empresas() devolve (precisa ter
             pelo menos id, regime, grupo, e idealmente conta_clientes/
             conta_fornecedores se disponíveis).
    grupo:   "ativo" | "passivo" | "despesas" | "receitas"

    Devolve lista de {"codigo": ..., "nome": ...}, sem duplicar, na ordem:
    comuns -> específicos do regime -> específico do modelo de negócio.
    """
    if grupo not in ("ativo", "passivo", "despesas", "receitas"):
        raise ValueError(f"grupo inválido: {grupo!r}")

    regime = empresa.get("regime")
    modelo = empresa.get("grupo")  # "comercio" | "servicos" — nome de campo
                                     # meio confuso (mesmo nome do parâmetro
                                     # "grupo" desta função, que é Ativo/
                                     # Passivo/Despesas/Receitas), mas é o
                                     # nome que já existe na tabela Empresa,
                                     # não vale a pena renomear só por isso.

    sugeridos = list(ACESSOS_COMUNS.get(grupo, []))
    sugeridos += ACESSOS_POR_REGIME.get(regime, {}).get(grupo, [])

    campo_conta = GRUPOS_POR_MODELO.get(modelo, {}).get(grupo)
    if campo_conta:
        codigo = empresa.get(campo_conta)
        if codigo:
            sugeridos.append({"codigo": codigo, "nome": NOMES_CONTA_MODELO[campo_conta]})

    return sugeridos