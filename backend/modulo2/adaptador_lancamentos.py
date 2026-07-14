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

  Módulo 2 (LancamentoBanco):
    .data       date completo (precisa do ano)
    .tipo       "C" / "D"
    .valor      sempre positivo
    .historico / .detalhe   texto (usamos o mesmo .raw pros dois campos)
"""
import datetime
try:
    from .modelos import LancamentoBanco
except ImportError:
    from modelos import LancamentoBanco


def converter_lancamentos_base(lancamentos_base: list, ano: int) -> list:
    """
    ano: o ano do extrato (o parser do Módulo 1 só devolve "DD/MM", sem
    ano — vem do mês/ano informado no upload, ex: "05/2026" -> ano=2026).
    """
    resultado = []
    for lb in lancamentos_base:
        dia, mes = lb.data.split("/")
        texto = (getattr(lb, "raw", None) or lb.descricao or "").strip()
        resultado.append(LancamentoBanco(
            data=datetime.date(ano, int(mes), int(dia)),
            historico=texto,
            detalhe=texto,
            valor=abs(lb.valor),
            tipo="D" if lb.valor < 0 else "C",
        ))
    return resultado