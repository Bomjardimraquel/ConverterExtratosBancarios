"""
Ponte entre o Módulo 1 (parsers de banco) e o Módulo 2 (motor de
cruzamento) — os dois usam um formato de lançamento ligeiramente
diferente, então precisa converter:

  Módulo 1 (LancamentoBase):
    .data       "DD/MM" (string, sem ano — o parser nunca soube o ano,
                 só o dia/mês que aparece no extrato)
    .tipo       "Crédito" / "Débito" (por extenso)
    .valor      com sinal (positivo = crédito, negativo = débito)
    .raw        texto original do extrato, sem formatação nenhuma
    .descricao  texto já formatado bonito ("Vr. ref. pix recebido de
                Fulano conf. extrato") — o mesmo que o Módulo 1 usa no
                Excel dele

  Módulo 2 (LancamentoBanco):
    .data       date completo (precisa do ano)
    .tipo       "C" / "D"
    .valor      sempre positivo
    .historico / .detalhe     texto CRU (usamos o .raw pros dois campos)
                               — precisa ser o cru mesmo, é o que bate
                               regra de texto/título por palavra-chave
    .descricao_formatada       a versão bonita (.descricao do Módulo 1)
                               — usada na planilha final quando não
                               casa com nada mais específico
"""
import datetime
try:
    from .modelos import LancamentoBanco
except ImportError:
    from modelos import LancamentoBanco


def converter_lancamentos_base(lancamentos_base: list, ano: int) -> list:
    
    resultado = []
    for lb in lancamentos_base:
        dia, mes = lb.data.split("/")
        texto_cru = (getattr(lb, "raw", None) or lb.descricao or "").strip()
        resultado.append(LancamentoBanco(
            data=datetime.date(ano, int(mes), int(dia)),
            historico=texto_cru,
            detalhe=texto_cru,
            valor=abs(lb.valor),
            tipo="D" if lb.valor < 0 else "C",
            descricao_formatada=(lb.descricao or "").strip() or None,
        ))
    return resultado