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