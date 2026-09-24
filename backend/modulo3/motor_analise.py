"""
MotorAnaliseRazao — regras "Nível 1": tudo aqui é mecânico, derivado só do
que está dentro do próprio razão, sem cadastro nenhum por empresa. Cada
regra recebe um (ou uma lista de) BlocoConta e devolve list[Achado] (pode
ser vazia).

Pares de reconciliação Passivo↔Despesa e listas de contas retificadoras
esperadas (Nível 2) NÃO estão aqui — dependem de cadastro que ainda não
existe, ficam pra próxima etapa.
"""
import re
from collections import Counter, defaultdict
from datetime import date
from typing import Optional

try:
    from .modelos import Achado, BlocoConta
except ImportError:
    from modelos import Achado, BlocoConta

TOLERANCIA_ARITMETICA = 0.02

# top 5 concentrando mais que isso do total positivo em aberto
CONCENTRACAO_MEDIO_PCT = 0.35
CONCENTRACAO_ALTO_PCT = 0.50

# dias sem nenhum lançamento novo numa conta com saldo em aberto
AGING_MEDIO_DIAS = 60
AGING_ALTO_DIAS = 120
# abaixo desse valor, aging não some da lista, só não grita "Alto"/"Médio"
AGING_VALOR_MINIMO = 500.0

# diferença entre provisionado e pago numa competência, como % do que
# foi provisionado — abaixo disso é arredondamento, não achado
FECHAMENTO_TOLERANCIA_PCT = 0.01
FECHAMENTO_TOLERANCIA_MINIMA = 0.10  # e nunca menos que 10 centavos
FECHAMENTO_MEDIO_PCT = 0.15
FECHAMENTO_ALTO_PCT = 0.50

# contas cujo nome geralmente autoriza saldo devedor temporário no
# Passivo, entre a provisão e o pagamento (visto em Cofins/FGTS/INSS a
# Recolher nesta sessão) — heurística de nome, não é cadastro por empresa
_PASSIVO_TOLERA_DEVEDOR_RE = re.compile(r"a Recolher|a Pagar|^Prov\.", re.IGNORECASE)

_COMPETENCIA_RE = re.compile(
    r"ref\.?\s*(?:m[êe]s|comp\.?)\s*(\d{2})/(\d{4})", re.IGNORECASE
)

# segundo formato de competência usado pelo Prosoft nas linhas de
# provisão geradas pela folha ("...s/folha pgto JAN/2026", "c/fol
# FEV/2026", "c/Resc MAR/2026 FULANO DE TAL") — mês abreviado em vez de
# "ref.mês XX/AAAA", que só aparece nas linhas de pagamento ("Pg....")
_MESES_ABREV = {
    "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
}
_COMPETENCIA_NOME_RE = re.compile(
    r"\b(JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ)/(\d{4})\b", re.IGNORECASE
)


def _extrair_competencia(historico: str) -> Optional[int]:
    """Acha a competência (índice ano*12+mês) citada no histórico, testando
    os dois formatos que o Prosoft usa. Devolve None se não achar nenhum —
    quem chama decide o que fazer com lançamentos sem competência clara."""
    m = _COMPETENCIA_RE.search(historico or "")
    if m:
        return _indice_mes(int(m.group(2)), int(m.group(1)))
    m2 = _COMPETENCIA_NOME_RE.search(historico or "")
    if m2:
        mes = _MESES_ABREV.get(m2.group(1).upper())
        if mes:
            return _indice_mes(int(m2.group(2)), mes)
    return None


def _achado_conta(bloco: BlocoConta, tipo, descricao, severidade, valor=None, referencia=None):
    return Achado(
        grupo=bloco.grupo, acesso=bloco.acesso, nome_conta=bloco.nome,
        terceiro=bloco.terceiro_nome, tipo=tipo, descricao=descricao,
        severidade=severidade, valor=valor, referencia=referencia,
    )


def regra_consistencia_aritmetica(bloco: BlocoConta) -> Optional[Achado]:
    calculado = bloco.saldo_anterior + bloco.debito_total - bloco.credito_total
    diff = calculado - bloco.saldo_final
    if abs(diff) <= TOLERANCIA_ARITMETICA:
        return None
    return _achado_conta(
        bloco, "inconsistencia_aritmetica",
        f"Saldo Anterior + Débito − Crédito = {calculado:,.2f}, mas o Saldo Final "
        f"impresso é {bloco.saldo_final:,.2f} (diferença de {diff:,.2f}).",
        "Alto", valor=diff,
    )


def regra_sinal_saldo(bloco: BlocoConta) -> Optional[Achado]:
    grupo, nome, sf = bloco.grupo, bloco.nome, bloco.saldo_final
    if abs(sf) <= TOLERANCIA_ARITMETICA:
        return None

    if grupo in ("ativo", "despesas") and sf < 0:
        return _achado_conta(
            bloco, "sinal_saldo_invertido",
            f"Conta de {grupo.capitalize()} (devedora por natureza) fechou com saldo "
            f"credor de R$ {abs(sf):,.2f}.",
            "Alto", valor=sf,
        )

    if grupo == "receitas" and sf > 0 and not nome.strip().startswith("(-)"):
        return _achado_conta(
            bloco, "sinal_saldo_invertido",
            f"Conta de Receita (credora por natureza) fechou com saldo devedor de "
            f"R$ {sf:,.2f}.",
            "Alto", valor=sf,
        )

    if grupo == "passivo" and sf > 0:
        # devedor no Passivo é normal em contas "a Recolher/a Pagar" entre
        # a provisão e o pagamento — rebaixa a severidade em vez de
        # suprimir, porque também pode ser sinal real de atraso acumulado
        severidade = "Médio" if _PASSIVO_TOLERA_DEVEDOR_RE.search(nome) else "Alto"
        return _achado_conta(
            bloco, "sinal_saldo_invertido",
            f"Conta de Passivo (credora por natureza) fechou com saldo devedor de "
            f"R$ {sf:,.2f}.",
            severidade, valor=sf,
        )

    return None


def _indice_mes(ano: int, mes: int) -> int:
    return ano * 12 + mes


def _de_indice_mes(indice: int) -> tuple:
    return divmod(indice - 1, 12)[0], divmod(indice - 1, 12)[1] + 1


def _passo_dominante(indices_ordenados: list) -> int:
    """
    Infere a cadência típica da conta (1 = mensal, 3 = trimestral...) pelo
    intervalo mais comum entre competências consecutivas — sem isso, uma
    conta trimestral (Provisão de IR/CSLL) dispara falso positivo todo
    mês que não é março/junho/setembro/dezembro.
    """
    diffs = [b - a for a, b in zip(indices_ordenados, indices_ordenados[1:])]
    if not diffs:
        return 1
    return Counter(diffs).most_common(1)[0][0]


_PROVISAO_RE = re.compile(r"^Vlr\.?\s*prov", re.IGNORECASE)
_PAGAMENTO_RE = re.compile(r"^Pg\.", re.IGNORECASE)
_RESCISAO_RE = re.compile(r"\bresc\b|rescis", re.IGNORECASE)


def _buracos_em_competencias(competencias: set, data_referencia: Optional[date], margem_meses: int = 2):
    """
    Núcleo comum das checagens de buraco de competência (provisão ou
    pagamento): dado um conjunto de índices de mês já vistos, infere a
    cadência e devolve os que faltam no meio ou no fim da série. Devolve
    (faltando, passo, inicio, fim) — quem chama decide o texto/severidade.
    """
    if len(competencias) < 2:
        return [], None, None, None

    indices_ordenados = sorted(competencias)
    passo = _passo_dominante(indices_ordenados)
    inicio, fim = indices_ordenados[0], indices_ordenados[-1]

    if data_referencia:
        # granularidade por mês, com folga: a competência mais recente
        # ainda pode estar dentro do prazo normal de registro/pagamento
        indice_hoje = _indice_mes(data_referencia.year, data_referencia.month)
        while indice_hoje - (fim + passo) >= margem_meses:
            fim += passo

    esperado = range(inicio, fim + 1, passo)
    faltando = [i for i in esperado if i not in competencias]
    return faltando, passo, inicio, fim


def regra_buraco_provisao(bloco: BlocoConta, data_referencia: Optional[date] = None) -> list:
    """
    A checagem que importa de verdade: existe uma provisão pra cada
    competência? A competência aqui vem da DATA do próprio lançamento
    de provisão (mês em que foi lançada), não de texto "ref.mês" — a
    maioria das provisões não referencia mês explicitamente no histórico,
    é o mês em que ela é lançada que já É a competência.
    """
    competencias = {
        _indice_mes(l.data.year, l.data.month)
        for l in bloco.lancamentos
        if _PROVISAO_RE.match(l.historico or "") and not _RESCISAO_RE.search(l.historico or "")
    }
    faltando, passo, inicio, fim = _buracos_em_competencias(competencias, data_referencia)
    if not faltando:
        return []

    return [
        _achado_conta(
            bloco, "buraco_provisao",
            f"Não encontrei provisão lançada na competência {mes:02d}/{ano} nesta conta "
            f"(cadência observada é de {passo} em {passo} mês(es), indo de "
            f"{_de_indice_mes(inicio)[1]:02d}/{_de_indice_mes(inicio)[0]} até "
            f"{_de_indice_mes(fim)[1]:02d}/{_de_indice_mes(fim)[0]}) — se a nota/conta "
            f"desse mês existe mas não foi provisionada, o saldo desta conta está "
            f"subestimado.",
            "Alto", referencia=f"{mes:02d}/{ano}",
        )
        for ano, mes in (_de_indice_mes(i) for i in faltando)
    ]


def regra_buraco_pagamento(bloco: BlocoConta, data_referencia: Optional[date] = None) -> list:
    """
    Pagamento em atraso é operacional, não contábil — por isso fica em
    severidade Médio (informativo) e não Alto: o que importa mais é a
    provisão existir e bater com o valor (regra_buraco_provisao e
    regra_provisao_diferente_pagamento), não a data do pagamento em si.
    """
    competencias = set()
    for l in bloco.lancamentos:
        if _RESCISAO_RE.search(l.historico or ""):
            continue  # rescisão é evento avulso, não faz parte do ciclo regular
        m = _COMPETENCIA_RE.search(l.historico or "")
        if m and _PAGAMENTO_RE.match(l.historico or ""):
            competencias.add(_indice_mes(int(m.group(2)), int(m.group(1))))

    faltando, passo, inicio, fim = _buracos_em_competencias(competencias, data_referencia)
    if not faltando:
        return []

    return [
        _achado_conta(
            bloco, "buraco_pagamento",
            f"Não encontrei pagamento referente à competência {mes:02d}/{ano} nesta conta "
            f"(cadência observada é de {passo} em {passo} mês(es), indo de "
            f"{_de_indice_mes(inicio)[1]:02d}/{_de_indice_mes(inicio)[0]} até "
            f"{_de_indice_mes(fim)[1]:02d}/{_de_indice_mes(fim)[0]}).",
            "Médio", referencia=f"{mes:02d}/{ano}",
        )
        for ano, mes in (_de_indice_mes(i) for i in faltando)
    ]


def regra_provisao_diferente_pagamento(bloco: BlocoConta) -> list:
    """
    Reconciliação exata por competência: soma TODO lançamento a crédito
    que cita aquela competência no histórico — não só as linhas que
    começam com "Vlr.prov" (isso excluía coisa que também compõe o valor
    devido daquele mês, tipo o desconto retido do funcionário e ajustes
    de rescisão) — e compara com o total pago naquela competência (linhas
    "Pg." que citam a mesma competência). Rescisão entra no total, porque
    ela é uma cobrança a mais dentro da mesma competência, não um evento
    à parte (diferente de regra_buraco_provisao/regra_buraco_pagamento,
    onde ela só atrapalharia a leitura da cadência mensal).

    Cada achado lista os números de lançamento dos dois lados, pra achar
    rápido no Prosoft qual lançamento específico está causando a
    diferença — em vez de só apontar "o saldo está estranho".
    """
    provisao_por_competencia = defaultdict(float)
    provisao_lancs = defaultdict(list)
    pagamento_por_competencia = defaultdict(float)
    pagamento_lancs = defaultdict(list)

    for l in bloco.lancamentos:
        indice = _extrair_competencia(l.historico or "")
        if indice is None:
            continue
        if l.credito > 0:
            provisao_por_competencia[indice] += l.credito
            provisao_lancs[indice].append(l.lancamento or "s/nº")
        elif _PAGAMENTO_RE.match(l.historico or "") and l.debito > 0:
            pagamento_por_competencia[indice] += l.debito
            pagamento_lancs[indice].append(l.lancamento or "s/nº")

    achados = []
    for indice in sorted(set(provisao_por_competencia) & set(pagamento_por_competencia)):
        provisionado = provisao_por_competencia[indice]
        pago = pagamento_por_competencia[indice]
        if provisionado <= TOLERANCIA_ARITMETICA:
            continue

        diff = provisionado - pago
        pct = abs(diff) / provisionado
        if pct < FECHAMENTO_TOLERANCIA_PCT or abs(diff) < FECHAMENTO_TOLERANCIA_MINIMA:
            continue  # arredondamento de centavos, não é achado

        if pct >= FECHAMENTO_ALTO_PCT:
            severidade = "Alto"
        elif pct >= FECHAMENTO_MEDIO_PCT:
            severidade = "Médio"
        else:
            severidade = "Baixo"

        ano, mes = _de_indice_mes(indice)
        lancs_prov = ", ".join(provisao_lancs[indice])
        lancs_pag = ", ".join(pagamento_lancs[indice])
        achados.append(_achado_conta(
            bloco, "provisao_diferente_pagamento",
            f"Competência {mes:02d}/{ano}: provisionado R$ {provisionado:,.2f} "
            f"(lançs {lancs_prov}), pago R$ {pago:,.2f} (lanç {lancs_pag}) — "
            f"diferença de R$ {diff:,.2f} ({pct:.0%} do provisionado). Confira "
            f"esses lançamentos no Prosoft pra achar de onde vem a diferença.",
            severidade, valor=diff, referencia=f"{mes:02d}/{ano}",
        ))
    return achados


def regra_rescisao_com_saldo_anterior_zerado(bloco: BlocoConta) -> list:
    """
    Pagamento de rescisão referenciando uma competência bem anterior ao
    período do razão, numa conta com Saldo Anterior R$ 0,00, é sinal de
    que aquela obrigação pode já existir de antes e não ter sido
    carregada — mesmo problema do Saldo Anterior zerado que já vimos em
    Clientes, só que aqui não dá pra confirmar comparando com um
    balancete (é achado só de uma conta, sem Terceiro pra somar), por
    isso vira um alerta pra conferência manual, não uma inconsistência.
    """
    if abs(bloco.saldo_anterior) > TOLERANCIA_ARITMETICA:
        return []  # Saldo Anterior já tem valor, não é o caso

    achados = []
    for l in bloco.lancamentos:
        if not re.search(r"\bresc\b|rescis", l.historico or "", re.IGNORECASE):
            continue
        m = _COMPETENCIA_RE.search(l.historico or "")
        if not m:
            continue
        mes, ano = int(m.group(1)), int(m.group(2))
        competencia = date(ano, mes, 1)
        if (l.data.year - ano) < 1:
            continue  # rescisão paga no mesmo ano/ano seguinte da competência, nada de estranho
        valor = l.debito or l.credito
        achados.append(_achado_conta(
            bloco, "rescisao_saldo_anterior_zerado",
            f"Pagamento de rescisão em {l.data.strftime('%d/%m/%Y')} referenciando a "
            f"competência {mes:02d}/{ano} (bem anterior ao período deste razão), numa "
            f"conta com Saldo Anterior R$ 0,00. Se essa obrigação já existia antes do "
            f"período coberto, vale confirmar que o zeramento do Saldo Anterior está "
            f"correto — pode ser que essa dívida estivesse em aberto o tempo todo sem "
            f"aparecer em nenhum saldo.",
            "Médio", valor=valor, referencia=l.lancamento,
        ))
    return achados


def regra_saldo_anterior_zerado(blocos: list) -> Optional[Achado]:
    if len(blocos) < 2:
        return None  # amostra pequena demais pra falar em "padrão"

    zerados = sum(1 for b in blocos if abs(b.saldo_anterior) <= TOLERANCIA_ARITMETICA)
    pct = zerados / len(blocos)
    if pct < 0.8:
        return None

    exemplo = blocos[0]
    return Achado(
        grupo=exemplo.grupo, acesso=exemplo.acesso, nome_conta=exemplo.nome,
        tipo="saldo_anterior_zerado_geral",
        descricao=(
            f"{zerados} de {len(blocos)} contas/terceiros deste arquivo ({pct:.0%}) têm "
            f"Saldo Anterior R$ 0,00 — parece que este razão foi exportado sem trazer o "
            f"saldo de abertura real. Isso também deixa o Saldo Final parcial (só reflete "
            f"o que está neste arquivo, não o saldo real acumulado), então os achados de "
            f"sinal de saldo abaixo foram suprimidos nas contas afetadas — não dava pra "
            f"confiar neles pela mesma causa. Vale cruzar com o balancete ou reexportar "
            f"com o Saldo Anterior incluído antes de confiar em saldo de qualquer conta "
            f"deste arquivo."
        ),
        severidade="Médio",
    )


def regra_concentracao_e_aging(blocos: list, data_referencia: Optional[date] = None) -> list:
    achados = []
    por_acesso = defaultdict(list)
    for b in blocos:
        if b.tem_terceiro:
            por_acesso[b.acesso].append(b)

    for acesso, grupo_blocos in por_acesso.items():
        if len(grupo_blocos) < 5:
            continue  # concentração só faz sentido com uma amostra razoável

        positivos = [b for b in grupo_blocos if b.saldo_final > 0]
        total_positivo = sum(b.saldo_final for b in positivos)
        if total_positivo > 0:
            top5 = sorted(positivos, key=lambda b: -b.saldo_final)[:5]
            soma_top5 = sum(b.saldo_final for b in top5)
            pct = soma_top5 / total_positivo
            if pct >= CONCENTRACAO_ALTO_PCT:
                severidade = "Alto"
            elif pct >= CONCENTRACAO_MEDIO_PCT:
                severidade = "Médio"
            else:
                severidade = None
            if severidade:
                nomes = ", ".join(b.terceiro_nome for b in top5)
                achados.append(Achado(
                    grupo=grupo_blocos[0].grupo, acesso=acesso, nome_conta=grupo_blocos[0].nome,
                    tipo="concentracao_risco",
                    descricao=(
                        f"Os 5 maiores saldos ({nomes}) somam R$ {soma_top5:,.2f}, "
                        f"{pct:.0%} de todo o saldo em aberto nesta conta "
                        f"(R$ {total_positivo:,.2f})."
                    ),
                    severidade=severidade, valor=soma_top5,
                ))

        if data_referencia:
            for b in positivos:
                # não só a data — pega o lançamento inteiro, pra poder citar
                # o número dele (acha rápido no Prosoft qual é)
                ultimo_lanc = max(b.lancamentos, key=lambda l: l.data, default=None)
                if ultimo_lanc is None:
                    continue
                ultimo = ultimo_lanc.data
                dias = (data_referencia - ultimo).days
                if dias >= AGING_ALTO_DIAS:
                    severidade = "Alto"
                elif dias >= AGING_MEDIO_DIAS:
                    severidade = "Médio"
                else:
                    continue
                if b.saldo_final < AGING_VALOR_MINIMO:
                    severidade = "Baixo"  # ainda aparece, só não com a mesma urgência
                achados.append(_achado_conta(
                    b, "saldo_parado",
                    f"Saldo em aberto de R$ {b.saldo_final:,.2f} sem nenhum lançamento "
                    f"novo há {dias} dias (último em {ultimo.strftime('%d/%m/%Y')}, "
                    f"lanç {ultimo_lanc.lancamento or 's/nº'}: \"{ultimo_lanc.historico}\").",
                    severidade, valor=b.saldo_final, referencia=ultimo_lanc.lancamento,
                ))

    return achados


def analisar(blocos: list, data_referencia: Optional[date] = None) -> list:
    """Roda todas as regras Nível 1 e devolve a lista completa de achados."""
    achados = []

    achado_saldo_anterior = regra_saldo_anterior_zerado(blocos)
    if achado_saldo_anterior:
        achados.append(achado_saldo_anterior)

    for bloco in blocos:
        a = regra_consistencia_aritmetica(bloco)
        if a:
            achados.append(a)

        # com Saldo Anterior sistemicamente ausente no arquivo, o Saldo
        # Final também fica parcial — só confia no sinal quando ESTE
        # bloco especificamente tem Saldo Anterior real (arquivo misto)
        # ou quando o arquivo como um todo não tem esse problema
        pode_confiar_no_sinal = (
            achado_saldo_anterior is None or abs(bloco.saldo_anterior) > TOLERANCIA_ARITMETICA
        )
        if pode_confiar_no_sinal:
            a = regra_sinal_saldo(bloco)
            if a:
                achados.append(a)

        achados.extend(regra_buraco_provisao(bloco, data_referencia))
        achados.extend(regra_buraco_pagamento(bloco, data_referencia))
        achados.extend(regra_provisao_diferente_pagamento(bloco))
        achados.extend(regra_rescisao_com_saldo_anterior_zerado(bloco))

    achados.extend(regra_concentracao_e_aging(blocos, data_referencia))

    ordem_severidade = {"Alto": 0, "Médio": 1, "Baixo": 2, "OK": 3}
    achados.sort(key=lambda a: ordem_severidade.get(a.severidade, 9))
    return achados