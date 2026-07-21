"""
Motor de cruzamento do Módulo 2.
"""

import re
import unicodedata
from datetime import date
from typing import Optional

try:
    from .modelos import (
        LancamentoBanco, Titulo, Despesa, NotaServico, DespesaJaLancada, LancamentoClassificado
    )
except ImportError:
    from modelos import (
        LancamentoBanco, Titulo, Despesa, NotaServico, DespesaJaLancada, LancamentoClassificado
    )


# ── Regras de texto GENÉRICAS ────────────────────────────────────────────────
# Valem pra QUALQUER empresa automaticamente, sem precisar escrever na
# config de cada uma — são as mesmas categorias que o Módulo 1 já
# classifica (classificador.py), só que aqui no formato que o
# _casa_regra_texto espera. Testadas antes só na Arandu/Diniz (que tinham
# a regra escrita à mão na config); isso corrige as outras 14 empresas
# que nunca tinham ganhado essa regra.
#
# Só têm "debito_D" (nunca "credito_C") de propósito: IOF/juros/tarifa só
# fazem sentido como despesa saindo do banco, nunca como entrada — o
# _casa_regra_texto já ignora essas regras sozinho quando o lançamento é
# crédito (falta credito_C, a regra não bate).
REGRAS_TEXTO_GENERICAS = [
    {
        "contem": ["IOF", "DEB.IOF", "DÉB.IOF", "IMPOSTO SOBRE OPERACAO FINANCEIRA"],
        "debito_D": "53513", "descricao": "IOF",
    },
    {
        "contem": [
            "JUROS", "JUROS CONTA GARANTIDA", "JUROS VENCIDOS", "ENCARGO",
            "MORA", "MULTA ATRASO", "JUROS EMPRESTIMO",
            "ENCARGOS FINANCEIROS", "JUROS FINANCIAMENTO",
        ],
        "debito_D": "53501", "descricao": "Juros",
    },
    {
        "contem": [
            "DEBITO PACOTE SERVICOS", "DÉBITO PACOTE SERVIÇOS", "PGS-CH PROP COOP",
            "PGS-CH PRÓP COOP", "TARIFA RENOVACAO LIMITE", "TARIFA RENOVAÇÃO LIMITE",
            "DEB.SEGURO PRESTAMISTA", "DÉB.SEGURO PRESTAMISTA",
            "TARIFA PACOTE DE SERVICOS", "TARIFA PACOTE DE SERVIÇOS",
            "SEG CRED PROTEG EMPRESA", "BB SEGURO",
            "TAR COBRANCA", "TAR COBRAN",
            "PACOTE DE SERVICO", "PACOTE SERVIÇO", "PACOTE DE SERVIÇOS",
            "PACOTE SERVICOS", "PACOTE SERVIÇOS",
            "TARIFA", "TARIFAS", "TAXA BANCARIA", "TAXA BANCÁRIA", "TAXA DE MANUT",
            "MANUTENCAO CONTA", "MANUTENÇÃO CONTA", "MENSALIDADE",
            "ANUIDADE", "COBRANCA MENSAL", "COBRANÇA MENSAL", "RENOVACAO CADASTRO",
            "RENOVAÇÃO CADASTRO", "EXTRATO BANCARIO", "EXTRATO BANCÁRIO",
            "TALAO", "TALÃO", "TED DOC TARIFA", "TARIFA PIX", "TARIFA TED",
            "TAR PROCESSAMENTO", "TARIF ADIC", "TARIFA FORNEC",
        ],
        "debito_D": "53502", "descricao": "Despesas Bancárias",
    },
]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    s = re.sub(r"[.,/&\-_]", " ", s)
    return " ".join(s.upper().split())


_STOPWORDS = {"DE", "DA", "DO", "DOS", "DAS", "E", "LTDA", "ME", "EPP", "SA", "S/A"}


def tokens(s: str) -> set:
    return {t for t in norm(s).split() if t not in _STOPWORDS and len(t) > 1}


def qtd_tokens_batem(tokens_a: set, tokens_b: set) -> int:
    usados_b = set()
    qtd = 0
    for a in tokens_a:
        for b in tokens_b:
            if b in usados_b:
                continue
            if a == b or (len(a) >= 3 and len(b) >= 3 and (a.startswith(b) or b.startswith(a))):
                usados_b.add(b)
                qtd += 1
                break
    return qtd


def primeiro_nome(s: str) -> str:
    for t in norm(s).split():
        if t not in _STOPWORDS and len(t) > 1:
            return t
    return ""


_RE_DATA_HORA = re.compile(r"^\s*\d{2}/\d{2}\s+\d{2}:\d{2}\s*")

_PREFIXOS_PIX = [
    r"PIX RECEB\.OUTRA IF\s*[-–]?\s*Recebimento Pix\s*",
    r"PIX RECEBIDO\s*[-–]?\s*OUTRA IF\s*[-–]?\s*Recebimento Pix\s*",
    r"TRANSF\.RECEBIDA\s*[-–]?\s*PIX SICOOB\s*[-–]?\s*",
    r"TRANSF\. RECEB\.\s*[-–]?\s*PIX SI[^\s]*\s*[-–]?\s*",
    r"PIX\s*[-–]\s*Recebido\s*",
    r"PIX RECEBIDO\s+\w+\d+/\d+\s+",
    r"Recebimento Pix\s*",
    r"REM\.:\s*",
    r"CRED\.TR\.CT\.INTERCRE\s*[-–]?\s*",
    r"CRÉD\.TED[-–]STR\s*[-–]?\s*",
    r"CRÉD\.TR\.CT\.INTERCRE\s*[-–]?\s*",
]


def extrai_nome_pagador(detalhe: str) -> str:
    texto = _RE_DATA_HORA.sub("", detalhe or "")
    for pat in _PREFIXOS_PIX:
        texto = re.sub(pat, "", texto, flags=re.IGNORECASE).strip()
    texto = re.sub(r"^[-–\s]+", "", texto).strip()
    texto = re.sub(r"\*{3}\.\d{3}\.\d{3}-\*{2}", "", texto).strip()
    texto = re.sub(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", "", texto).strip()
    texto = re.sub(r"\b\d{10,}\b", "", texto).strip()
    texto = re.sub(r"\b\d{2}\.\d{3}\.\d{3}\.\d{3}\.\d{3}\b", "", texto).strip()
    texto = re.sub(r"DOC\.:\s*\w+", "", texto, flags=re.IGNORECASE).strip()
    texto = re.sub(r"[-–\s]+$", "", texto).strip()
    texto = re.sub(r"\s+", " ", texto).strip()
    if len(texto) < 3 or re.match(r"^[\d\s.\-]+$", texto):
        return ""
    return texto[:50].strip()


def contem_termo(texto: str, termo: str) -> bool:
    t = norm(termo)
    if not t:
        return False
    return re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", texto) is not None


def so_digitos(s: str) -> str:
    return re.sub(r"\D", "", str(s or ""))


def eh_pj(cnpj_cpf: str) -> bool:
    return len(so_digitos(cnpj_cpf)) == 14


class MotorCruzamento:

    def __init__(self, config_empresa: dict, conta_banco: str):
        self.cfg = config_empresa
        self.conta_banco = conta_banco
        self.tol = config_empresa["cruzamento"]["tolerancia_valor"]
        self.janela_despesa = config_empresa["cruzamento"]["janela_dias_despesa"]

    def cruzar(
        self,
        lancamentos: list,
        despesas=None,
        titulos=None,
        notas=None,
        despesas_ja_lancadas=None,
        modo_despesas: str = None,
    ) -> list:
        # Se quem chamou já detectou o tipo do arquivo (ver
        # carregador_despesas.py) e passou explicitamente, usa isso.
        # Senão, cai no campo antigo da config (compatibilidade).
        modo_despesas = modo_despesas or self.cfg.get("modo_despesas", "despesa_classificada")

        despesas = list(despesas or [])
        titulos = list(titulos or [])
        notas = [n for n in (notas or []) if not n.cancelada]
        ja_lancadas = list(despesas_ja_lancadas or [])

        despesas_banco = [
            d for d in despesas
            if d.conta_credito is None or str(d.conta_credito) == str(self.conta_banco)
        ]

        self._enriquecer_despesas(despesas_banco, notas)

        usadas_desp: set = set()
        usados_tit: set = set()
        usadas_jal: set = set()
        resultado = []

        for lanc in lancamentos:
            if modo_despesas == "razao_prosoft":
                r = (
                    self._ja_lancado(lanc, ja_lancadas, usadas_jal)
                    or self._casa_titulo(lanc, titulos, usados_tit)
                    or self._casa_regra_texto(lanc)
                    or self._classificacao_simples(lanc)
                )
            else:
                r = (
                    self._casa_despesa(lanc, despesas_banco, usadas_desp)
                    or self._casa_titulo(lanc, titulos, usados_tit)
                    or self._casa_regra_texto(lanc)
                    or self._classificacao_simples(lanc)
                )
            resultado.append(r)

        self._avisos_de_sobras(resultado, despesas_banco, usadas_desp)
        if modo_despesas == "razao_prosoft":
            self._pendencias_razao(resultado, ja_lancadas, usadas_jal)
        return resultado

    @staticmethod
    def resultado_para_excel(resultado: list) -> list:
        ORIGENS_FORA_DA_PLANILHA = {"ja_lancado", "pendencia_razao", "pendencia_despesa"}
        return [r for r in resultado if r.origem not in ORIGENS_FORA_DA_PLANILHA]

    @staticmethod
    def resultado_pendencias(resultado: list) -> list:
        return [r for r in resultado if r.origem in ("pendencia_razao", "pendencia_despesa")]

    def _ja_lancado(self, lanc, ja_lancadas, usadas):
        for i, j in enumerate(ja_lancadas):
            if i in usadas:
                continue
            if j.tipo != lanc.tipo:
                continue
            if abs(j.valor - lanc.valor) >= self.tol:
                continue
            if abs((j.data - lanc.data).days) > self.janela_despesa:
                continue
            usadas.add(i)
            return LancamentoClassificado(
                data=lanc.data, descricao=self._descricao_padrao(lanc),
                valor=lanc.valor, tipo=lanc.tipo,
                origem="ja_lancado", confianca="alta", casada=True,
                referencia=j.historico[:40],
            )
        return None

    def _pendencias_razao(self, resultado, ja_lancadas, usadas):
        sobras = [j for i, j in enumerate(ja_lancadas) if i not in usadas]
        if not sobras:
            return
        for j in sobras:
            resultado.append(LancamentoClassificado(
                data=j.data, descricao=f"[PENDÊNCIA] {j.historico}",
                valor=j.valor, tipo=j.tipo,
                origem="pendencia_razao", confianca="baixa", casada=False,
                aviso=(
                    "Está lançado no Prosoft (razão) mas não achei no extrato — "
                    "confirmar se foi realmente debitado no banco ou se é erro de digitação/duplicidade"
                ),
                referencia=j.historico[:40],
            ))

    def _casa_despesa(self, lanc, despesas, usadas):
        if lanc.tipo != "D":
            return None
        cands = []
        for i, d in enumerate(despesas):
            if i in usadas:
                continue
            if abs(d.valor - lanc.valor) >= self.tol:
                continue
            dif = abs((lanc.data - d.data).days)
            if dif <= self.janela_despesa:
                cands.append((dif, i, d))
        if not cands:
            return None
        cands.sort(key=lambda x: x[0])
        dif, i, d = cands[0]
        usadas.add(i)

        if d.descricao_override:
            descricao = d.descricao_override
        else:
            partes = [p for p in (d.razao_social, d.descricao) if p]
            nome_despesa = " - ".join(partes) or lanc.detalhe.strip() or lanc.historico
            descricao = f"Pg. ref. {nome_despesa}"

        return LancamentoClassificado(
            data=lanc.data, descricao=descricao,
            valor=lanc.valor, tipo=lanc.tipo,
            conta_debito=str(d.conta_debito or ""),
            conta_credito=str(d.conta_credito or self.conta_banco),
            origem="despesa", confianca=(d.confianca or "alta"), casada=True,
            aviso=d.aviso or "",
            referencia=f"despesa {d.data} {d.razao_social[:25]}",
        )

    def _casa_titulo(self, lanc, titulos, usados):
        detalhe = norm(lanc.detalhe)
        intermediarios = self.cfg.get("intermediarios_financeiros", [])
        eh_intermediario = any(contem_termo(detalhe, nome) for nome in intermediarios)

        janela_venc = self.cfg["cruzamento"].get("janela_dias_titulo_pj", 30)

        cands = []
        for i, t in enumerate(titulos):
            if i in usados:
                continue
            if abs(t.valor - lanc.valor) >= self.tol:
                continue
            if lanc.tipo == "C" and t.tipo != "receber":
                continue
            if lanc.tipo == "D" and t.tipo != "pagar":
                continue

            if eh_intermediario:
                if abs((t.vencimento - lanc.data).days) <= janela_venc:
                    cands.append((i, t))
            else:
                tk = tokens(t.nome)
                if qtd_tokens_batem(tk, tokens(detalhe)) >= 2:
                    if not eh_pj(t.cnpj_cpf):
                        if primeiro_nome(t.nome) != primeiro_nome(detalhe):
                            continue
                    cands.append((i, t))
        if not cands:
            return None

        cands.sort(key=lambda x: abs((x[1].vencimento - lanc.data).days))
        i, t = cands[0]

        pj = eh_pj(t.cnpj_cpf)
        if not pj and not self.cfg.get("casa_pf", False):
            return LancamentoClassificado(
                data=lanc.data, descricao=self._descricao_padrao(lanc),
                valor=lanc.valor, tipo=lanc.tipo,
                **self._contas_simples(lanc),
                origem="simples", confianca="baixa", casada=False,
                aviso=f"Convergência PF: parece ser o título {t.docto} de {t.nome[:30]} — confirmar manualmente",
                referencia=t.docto,
            )

        usados.add(i)
        confianca = "media" if eh_intermediario else "alta"
        aviso_intermediario = (
            f"Pago via intermediário financeiro (duplicata descontada) — fornecedor original: {t.nome[:35]} — confirmar"
            if eh_intermediario else ""
        )

        if t.pago:
            return LancamentoClassificado(
                data=lanc.data, descricao=self._descricao_padrao(lanc),
                valor=lanc.valor, tipo=lanc.tipo,
                origem="titulo", confianca=confianca, casada=True,
                aviso=f"JÁ BAIXADO no Prosoft em {t.data_pagto} (título {t.docto}) — pode descartar",
                referencia=t.docto,
            )

        codigo_terceiro = self._terceiro_por_nome(t.nome)
        if lanc.tipo == "C":
            return LancamentoClassificado(
                data=lanc.data, descricao=self._descricao_padrao(lanc),
                valor=lanc.valor, tipo=lanc.tipo,
                conta_debito=self.conta_banco,
                conta_credito=self.cfg["conta_clientes"],
                terceiro_credito=codigo_terceiro,
                origem="titulo", confianca=confianca, casada=True,
                aviso=aviso_intermediario,
                referencia=t.docto,
            )
        else:
            return LancamentoClassificado(
                data=lanc.data, descricao=self._descricao_padrao(lanc),
                valor=lanc.valor, tipo=lanc.tipo,
                conta_debito=self.cfg["conta_fornecedores"],
                terceiro_debito=codigo_terceiro,
                conta_credito=self.conta_banco,
                origem="titulo", confianca=confianca, casada=True,
                aviso=aviso_intermediario,
                referencia=t.docto,
            )

    def _casa_regra_texto(self, lanc):
        texto = norm(lanc.historico + " " + lanc.detalhe)
        # Regras da empresa primeiro (pode ter algo específico que bate
        # antes da genérica), depois as genéricas (IOF/juros/despesas
        # bancárias) — valendo pra QUALQUER empresa, sem precisar
        # escrever isso na config de cada uma.
        for lista_regras in (self.cfg.get("regras_texto", []), REGRAS_TEXTO_GENERICAS):
            resultado = self._tentar_lista_regras_texto(lanc, texto, lista_regras)
            if resultado:
                return resultado
        return None

    def _tentar_lista_regras_texto(self, lanc, texto, lista_regras):
        for regra in lista_regras:
            if regra.get("contem_todos"):
                bate = all(contem_termo(texto, p) for p in regra["contem_todos"])
            else:
                bate = any(contem_termo(texto, p) for p in regra.get("contem", []))

            if bate:
                if any(contem_termo(texto, p) for p in regra.get("nao_contem", [])):
                    continue

                if regra.get("usa_padrao"):
                    contas = self._contas_simples(lanc)
                    conta_d, conta_c = contas["conta_debito"], contas["conta_credito"]
                    template = regra.get("descricao_template", "")
                    if "{nome}" in template:
                        nome = extrai_nome_pagador(lanc.detalhe)
                        descricao = template.format(nome=nome) if nome else \
                            regra.get("descricao_sem_nome", template.replace(" {nome}", "").replace("{nome}", ""))
                    else:
                        descricao = template or self._descricao_padrao(lanc)
                else:
                    if lanc.tipo == "D":
                        conta_d = regra.get("debito_D", "")
                        conta_c = self.conta_banco
                    else:
                        conta_d = self.conta_banco
                        conta_c = regra.get("credito_C", "")
                    if not (conta_d and conta_c):
                        continue
                    if regra.get("descricao_dinamica"):
                        descricao = self._descricao_padrao(lanc)
                    else:
                        descricao = regra.get("descricao", "") or self._descricao_padrao(lanc)

                return LancamentoClassificado(
                    data=lanc.data,
                    descricao=descricao,
                    valor=lanc.valor, tipo=lanc.tipo,
                    conta_debito=conta_d, conta_credito=conta_c,
                    origem="regra_texto",
                    confianca=regra.get("confianca", "media"),
                    casada=True,
                    aviso=regra.get("aviso", ""),
                )
        return None

    def _classificacao_simples(self, lanc):
        return LancamentoClassificado(
            data=lanc.data, descricao=self._descricao_padrao(lanc),
            valor=lanc.valor, tipo=lanc.tipo,
            **self._contas_simples(lanc),
            origem="simples", confianca="baixa", casada=False,
            aviso="Sem correspondência — revisar classificação",
        )

    def _descricao_padrao(self, lanc) -> str:
        """
        Descrição a usar quando nada mais específico (título, despesa,
        regra de texto com descrição própria) definiu uma — prefere a
        versão já formatada pelo Módulo 1 ("Vr. ref. pix recebido de
        Fulano conf. extrato"), porque o texto cru do extrato direto no
        Prosoft fica feio. Só cai pro texto cru se por algum motivo a
        formatada não existir.
        """
        return lanc.descricao_formatada or lanc.detalhe.strip() or lanc.historico

    def _contas_simples(self, lanc):
        caixa = self.cfg.get("conta_caixa", "11002")
        if lanc.tipo == "C":
            return {"conta_debito": self.conta_banco, "conta_credito": caixa}

        # Saída sem nenhum match (fornecedor/despesa/título/regra de texto
        # já falharam até aqui — é aqui que 'conta_simples' entra em jogo
        # de qualquer forma). Se a empresa tiver uma conta configurada pra
        # esse caso (ex: Diniz manda pra "Diversos" 53065 em vez de caixa,
        # pra não misturar saída sem fornecedor identificado com o
        # movimento normal de caixa), usa ela; senão segue o padrão de
        # sempre (caixa).
        conta_saida_sem_match = self.cfg.get("conta_saida_sem_match")
        if conta_saida_sem_match:
            return {"conta_debito": conta_saida_sem_match, "conta_credito": self.conta_banco}

        return {"conta_debito": caixa, "conta_credito": self.conta_banco}

    def _terceiro_por_nome(self, nome: str) -> str:
        n = norm(nome)
        for prefixo, codigo in self.cfg.get("terceiros_fornecedores", {}).items():
            if n.startswith(norm(prefixo)):
                return codigo
        for prefixo, codigo in self.cfg.get("terceiros_clientes", {}).items():
            if n.startswith(norm(prefixo)):
                return codigo
        return ""

    def _enriquecer_despesas(self, despesas, notas):
        if not notas:
            return
        for d in despesas:
            if d.razao_social:
                continue
            for n in notas:
                if abs(n.valor - d.valor) < self.tol:
                    d.razao_social = n.razao_social
                    break

    def _avisos_de_sobras(self, resultado, despesas, usadas):
        sobras = [d for i, d in enumerate(despesas) if i not in usadas]
        for d in sobras:
            resultado.append(LancamentoClassificado(
                data=d.data, descricao=f"Pg. ref. {d.razao_social or d.descricao}",
                valor=d.valor, tipo="D",
                origem="pendencia_despesa", confianca="baixa", casada=False,
                aviso="Despesa do arquivo não encontrada no extrato — possível quebra de pagamento, paga por outra conta, ou ainda não debitada",
                referencia=d.descricao,
            ))