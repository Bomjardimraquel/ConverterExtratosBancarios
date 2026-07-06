from parsers.factory import get_parser


def processar_extrato_job(
    conteudo: bytes,
    banco: str,
    conta_banco: str,
    nome_empresa: str = "",
    mes_ano: str = "",
) -> dict:

    parser = get_parser(banco, conta_banco)
    lancamentos = parser.parse(conteudo)

    if not lancamentos:
        raise ValueError(
            "Nenhum lançamento encontrado no PDF. "
            "Verifique se o banco selecionado está correto."
        )

    return {
        "total": len(lancamentos),
        "banco": banco,
        "nome_empresa": nome_empresa,
        "mes_ano": mes_ano,
        "lancamentos": [
            l if isinstance(l, dict) else l.to_dict() for l in lancamentos
        ],
    }