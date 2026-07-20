"""
Conexão com o Postgres. A string de conexão vem de uma variável de
ambiente (DATABASE_URL) — nunca escrita fixa no código, porque a senha
do banco muda de máquina pra máquina (local vs. Railway depois) e não
pode ir pro GitHub.

Formato esperado da variável, exemplo local:
  DATABASE_URL=postgresql://postgres:SUASENHA@localhost:5432/conciliador
"""
import os
from dotenv import load_dotenv
from sqlmodel import create_engine, Session

# Carrega backend/.env automaticamente — sem isso, só funcionaria se
# alguém tivesse configurado DATABASE_URL manualmente naquele terminal
# específico (e isso se perde assim que a janela fecha).
_CAMINHO_ENV = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(os.path.normpath(_CAMINHO_ENV))

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "Falta a variável de ambiente DATABASE_URL. Confirma que existe "
        "'backend/.env' com a linha DATABASE_URL=postgresql+psycopg2://"
        "postgres:SUASENHA@localhost:5432/conciliador"
    )

engine = create_engine(DATABASE_URL, echo=False)


def get_session():
    with Session(engine) as session:
        yield session