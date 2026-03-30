import pdfplumber
import re
import io
from parsers.base import ParserBase, LancamentoBase
from typing import List


class ParserItau(ParserBase):
    """
    Itaú — formato real extraído pelo pdfplumber.

    O PDF do Itaú tem colunas: Data | Lançamentos | Razão Social | CNPJ/CPF | Valor | Saldo
    O pdfplumber extrai o texto de formas variadas:

    Caso A (linha completa):
      "02/02/2026 PIX RECEBIDO APOLINA31/01 APOLINARIO DE JESUS SOUZA 655.521.805-34 25,00"

    Caso B (lançamento multilinhas — razão social na linha seguinte):
      "02/02/2026 RECEBIMENTO REDE ELO DB0087118734 01.425.787/0001-04 60,07"
      (linha anterior pode ter "REDECARD INSTITUICAO DE" e "PAGAMENTO S.A." flutuando)

    Caso C (sem razão social):
      "02/02/2026 PIX QRS 1.071,00"
      "03/02/2026 TAR COBRANCA EXP -21,00"

    Estratégia:
    - Coleta todas as linhas com data DD/MM/AAAA no início + valor no final
    - Linhas sem data mas com valor são ignoradas (saldo/header)
    - Valor negativo = débito
    """

    IGNORAR_RE = re.compile(
        r"saldo\s*(total|anterior|disponível)|lançamentos do período|"
        r"atualizado em|em caso de dúvida|reclamações|ouvidoria|sac\s|"
        r"itau\.com\.br|deficiente|^\s*$|data\s+lançamentos|"
        r"razão social|cnpj/cpf|valor\s*\(r\$\)|saldo\s*\(r\$\)|"
        r"limite da conta|aviso:|itaú",
        re.IGNORECASE
    )

    # Valor no final (pode ter - no início)
    VALOR_RE = re.compile(r"(-?\d{1,3}(?:\.\d{3})*,\d{2})\s*$")

    # CNPJ ou CPF para remover da descrição
    CNPJ_CPF_RE = re.compile(
        r"\s*\d{2,3}\.\d{3}\.\d{3}[/\-]\d{4,6}[-\s]?\d{0,2}\s*"
    )

    def parse(self, conteudo: bytes) -> List[LancamentoBase]:
        resultado = []
        with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
            for page in pdf.pages:
                texto = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                resultado += self._parse_pagina(texto.splitlines())
        return resultado

    def _parse_pagina(self, linhas: List[str]) -> List[LancamentoBase]:
        resultado = []
        # Junta linhas órfãs (sem data, sem valor) à linha com data anterior
        blocos = self._agrupar_linhas(linhas)

        for data, texto_completo in blocos:
            m_val = self.VALOR_RE.search(texto_completo)
            if not m_val:
                continue

            valor_str = m_val.group(1)
            texto_sem_val = texto_completo[:m_val.start()].strip()

            # Remove CNPJ/CPF
            historico = self.CNPJ_CPF_RE.sub(" ", texto_sem_val).strip()

            # Remove razão social longa (REDECARD INSTITUICAO DE PAGAMENTO S.A.)
            historico = self._limpar_historico(historico)

            if not historico or len(historico) < 3:
                continue
            if self.IGNORAR_RE.search(historico):
                continue

            try:
                valor = float(valor_str.replace(".", "").replace(",", "."))
            except ValueError:
                continue

            resultado.append(LancamentoBase(data, historico, valor, self.conta_banco))

        return resultado

    def _agrupar_linhas(self, linhas: List[str]):
        """
        Retorna lista de (data, texto_linha) agrupando continuações.
        Linhas sem data e sem valor são anexadas à linha com data anterior.
        """
        grupos = []  # [(data, texto)]
        for linha in linhas:
            linha = linha.strip()
            if not linha:
                continue
            if self.IGNORAR_RE.search(linha):
                continue

            m = re.match(r"^(\d{2}/\d{2}/\d{4})\s+(.*)", linha)
            if m:
                data = m.group(1)[:5]
                resto = m.group(2).strip()
                grupos.append([data, resto])
            else:
                # Linha sem data — pode ser continuação (razão social)
                # Só anexa se a linha tem letras e não tem valor sozinho
                if grupos and re.search(r"[A-Za-z]", linha) and not self.VALOR_RE.search(linha):
                    grupos[-1][1] += " " + linha

        return grupos

    def _limpar_historico(self, texto: str) -> str:
        """Remove razões sociais conhecidas e deixa só o tipo de lançamento."""
        # Remove "REDECARD INSTITUICAO DE PAGAMENTO S.A." e similares
        texto = re.sub(r"REDECARD\s+INSTITUICAO.*", "", texto, flags=re.IGNORECASE).strip()
        # Remove texto após hífen longo que seja razão social
        # Mantém o código do lançamento (DB0087118734, AT0087118734)
        # Limita a 80 chars
        return texto[:80].strip()
