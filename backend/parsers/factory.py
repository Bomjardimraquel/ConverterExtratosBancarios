from parsers.sicoob import ParserSicoob
from parsers.sicoob_aplic import ParserSicoobAplic
from parsers.bb import ParserBB
from parsers.itau import ParserItau
from parsers.pagbank import ParserPagBank
from parsers.santander import ParserSantander
from parsers.generico import ParserGenerico
from utils.contas import BANCO_CONTA


def get_parser(banco: str, conta_banco: str = None):
    banco_key = banco.lower().replace(" ", "_")
    if conta_banco is None:
        conta_banco = BANCO_CONTA.get(banco_key, "11002")

    parsers = {
        "sicoob": ParserSicoob,
        "emprestimo_sicoob": ParserSicoob,
        "sicoob_aplic": ParserSicoobAplic,
        "sicoob_aplicacao": ParserSicoobAplic,
        "bb": ParserBB,
        "banco_do_brasil": ParserBB,
        "bb_rende_facil": ParserBB,
        "emprestimo_bb": ParserBB,
        "itau": ParserItau,
        "itau_aplicacao": ParserItau,
        "pagbank": ParserPagBank,
        "santander": ParserSantander,
        "bradesco": ParserGenerico,
        "nordeste": ParserGenerico,
        "banco_nordeste": ParserGenerico,
    }

    ParserClass = parsers.get(banco_key, ParserGenerico)
    return ParserClass(conta_banco)