CONTAS = {
    "11041": "BB - Banco do Brasil",
    "11142": "BB Rende Fácil",
    "21381": "Empréstimo BB",
    "11120": "Sicoob",
    "21325": "Empréstimo Sicoob",
    "11161": "Sicoob Aplicação",
    "11045": "Itaú",
    "11146": "Itaú (Aplicação)",
    "11127": "PagBank",
    "11126": "Santander",
    "11044": "Bradesco",
    "11042": "Banco do Nordeste",
    "11002": "Caixa da Empresa",
    "53502": "Despesas Bancárias",
    "53513": "IOF",  # bug corrigido: estava 53514
    "53501": "Juros",
    "53065": "Diversos (Impostos)",
    "21504": "IRRF",
}

CONTA_CAIXA = "11002"

# Contas "especiais" — ao contrário de REGRAS_CLASSIFICACAO (que só vale
# pra débito e sempre credita o banco), essas valem pros DOIS lados
# (entrada E saída), porque representam uma transferência entre o banco e
# outra conta do próprio balanço (empréstimo, aplicação) — não é
# despesa/receita de verdade, é dinheiro só mudando de lugar dentro da
# empresa. Testadas ANTES de tudo em classificar_lancamento.
CONTAS_ESPECIAIS = [
    {
        "keywords": [
            "bb giro pronampe", "pronampe",
            "capital de gir", "capital de giro",
            "capital giro", "cap giro", "cap. giro",  # formas sem "de" — como aparece de verdade no extrato do BB
        ],
        "conta_especial": "21381",  # Empréstimo BB
        "nome": "Empréstimo BB (Giro/Pronampe)",
    },
    {
        "keywords": ["bb rende facil", "rende fácil"],
        "conta_especial": "11142",  # BB Rende Fácil (Aplicação)
        "nome": "BB Rende Fácil (Aplicação)",
    },
]

BANCO_CONTA = {
    "bb": "11041",
    "banco_do_brasil": "11041",
    "bb_rende_facil": "11142",
    "emprestimo_bb": "21381",
    "sicoob": "11120",
    "emprestimo_sicoob": "21325",
    "sicoob_aplic": "11161",
    "sicoob_aplicacao": "11161",
    "itau": "11045",
    "itau_aplicacao": "11146",
    "pagbank": "11127",
    "santander": "11126",
    "bradesco": "11044",
    "nordeste": "11042",
    "banco_nordeste": "11042",
}

# Regras de classificação especial para débitos
# Ordem importa: mais específica primeiro
REGRAS_CLASSIFICACAO = [
    # ── IOF ─────────────────────────────────────────────────────────────────
    {
        "keywords": ["iof", "deb.iof", "déb.iof", "imposto sobre operacao financeira"],
        "conta_despesa": "53513",  # bug corrigido: estava 53514
        "nome": "IOF",
    },
    # ── JUROS ────────────────────────────────────────────────────────────────
    {
        "keywords": [
            "juros", "juros conta garantida", "juros vencidos",
            "encargo", "mora", "multa atraso", "juros emprestimo",
            "encargos financeiros", "juros financiamento",
        ],
        "conta_despesa": "53501",
        "nome": "Juros",
    },
    # ── DESPESAS BANCÁRIAS ───────────────────────────────────────────────────
    {
        "keywords": [
            "debito pacote servicos", "débito pacote serviços", "pgs-ch prop coop",
            "pgs-ch próp coop", "tarifa renovacao limite", "tarifa renovação limite",
            "deb.seguro prestamista", "déb.seguro prestamista",
            "cheque pago caixa", "cheque compe integrada",
            "tarifa pacote de servicos", "tarifa pacote de serviços",
            "seg cred proteg empresa", "bb seguro", "bb giro pronampe",
            "tar cobranca", "tar cobran",
            "pacote de servico", "pacote serviço", "pacote de serviços",
            "tarifa", "tarif", "taxa bancaria", "taxa de manut",
            "manutencao conta", "manutenção conta", "mensalidade",
            "anuidade", "cobranca mensal", "renovacao cadastro",
            "cadastro", "extrato bancario", "talao", "talão",
            "ted doc tarifa", "tarifa pix", "tarifa ted",
        ],
        "conta_despesa": "53502",
        "nome": "Despesas Bancárias",
    },
    # ── IMPOSTOS / TRIBUTOS ──────────────────────────────────────────────────
    # NOTA: "irrf" está aqui dentro (cai em 53065, junto com DARF/ICMS/PIS/
    # COFINS genérico), não na conta própria "21504 - IRRF" que existe no
    # CONTAS. Confirmar com a Raquel se é proposital (tudo que é imposto no
    # extrato vira "despesa: diversos" no Módulo 1 e a conta certa é
    # ajustada na mão no Prosoft) ou se o IRRF deveria usar 21504 direto,
    # igual o IOF/Juros usam suas contas próprias.
    {
        "keywords": [
            "deb.conv.orgaos gov", "déb.conv.orgãos gov",
            "das - simples nacional", "simples nacional",
            "rfb-darf", "dae icms",
            "pagamentos pix qr-code receita federal",
            "pagamentos pix qr-code sefaz",
            "tributo", "imposto", "darf", "gps", "gare", "das",
            "inss", "fgts", "irrf", "iss", "icms", "pis", "cofins",
            "csll", "irpj", "contribuicao", "contribuição",
            "receita federal", "prefeitura", "sefaz", "secretaria da fazenda",
            "db.conv.tr fd", "rfb", "orgaos gov", "órgãos gov",
            "credito.ted-str bahia", "créd.ted-str bahia",
        ],
        "conta_despesa": "53065",
        "nome": "Diversos (Impostos)",
    },
]