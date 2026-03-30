CONTAS = {
    "11041": "BB - Banco do Brasil",
    "11142": "BB Rende Fácil",
    "21381": "Empréstimo BB",
    "11120": "Sicoob",
    "21325": "Empréstimo Sicoob",
    "11045": "Itaú",
    "11146": "Itaú (Aplicação)",
    "11127": "PagBank",
    "11126": "Santander",
    "11044": "Bradesco",
    "11042": "Banco do Nordeste",
    "11002": "Caixa da Empresa",
    "53502": "Despesas Bancárias",
    "53514": "IOF",
    "53501": "Juros",
    "53065": "Diversos (Impostos)",
}

CONTA_CAIXA = "11002"

BANCO_CONTA = {
    "bb": "11041",
    "banco_do_brasil": "11041",
    "bb_rende_facil": "11142",
    "emprestimo_bb": "21381",
    "sicoob": "11120",
    "emprestimo_sicoob": "21325",
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
        "conta_despesa": "53514",
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
            # Sicoob
            "debito pacote servicos", "débito pacote serviços", "pgs-ch prop coop",
            "pgs-ch próp coop", "tarifa renovacao limite", "tarifa renovação limite",
            "deb.seguro prestamista", "déb.seguro prestamista",
            "cheque pago caixa", "cheque compe integrada",
            # BB
            "tarifa pacote de servicos", "tarifa pacote de serviços",
            "seg cred proteg empresa", "bb seguro", "bb giro pronampe",
            # Itaú
            "tar cobranca", "tar cobran",
            # Genéricos
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
    {
        "keywords": [
            # Sicoob
            "deb.conv.orgaos gov", "déb.conv.orgãos gov",
            # BB
            "das - simples nacional", "simples nacional",
            "rfb-darf", "dae icms",
            # Itaú
            "pagamentos pix qr-code receita federal",
            "pagamentos pix qr-code sefaz",
            # Genéricos
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
