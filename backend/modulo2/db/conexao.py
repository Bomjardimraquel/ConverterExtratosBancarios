"""
Conexão com o Postgres. A string de conexão vem de uma variável de
ambiente (DATABASE_URL) — nunca escrita fixa no código, porque a senha
do banco muda de máquina pra máquina (local vs. Railway depois) e não
pode ir pro GitHub.

Formato esperado da variável, exemplo local:
  DATABASE_URL=postgresql://postgres:SUASENHA@localhost:5432/conciliador
"""
import os
from sqlmodel import create_engine, Session

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "Falta a variável de ambiente DATABASE_URL. Exemplo pra rodar "
        "local: postgresql://postgres:SUASENHA@localhost:5432/conciliador"
    )

engine = create_engine(DATABASE_URL, echo=False)


def get_session():
    with Session(engine) as session:
        yield session