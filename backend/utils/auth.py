from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from utils.fila import conexao_redis
import os

PRODUCAO = os.getenv("AMBIENTE") == "producao"

# Segredos e senhas agora vêm de variável de ambiente — não ficam mais
# escritos direto no código. Isso é o que permite esse arquivo continuar
# gitignored (nunca vai pro GitHub) e MESMO ASSIM funcionar no Railway:
# lá, os valores são configurados nas "Variables" do serviço, não em
# arquivo nenhum. Localmente, os mesmos nomes vão no .env de sempre.
SECRET_KEY = os.getenv("SECRET_KEY")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

if not SECRET_KEY or not REFRESH_SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY e REFRESH_SECRET_KEY precisam estar definidos como "
        "variável de ambiente (no .env local, ou nas Variables do Railway)."
    )

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Usuário "admin" removido de propósito — só os usuários reais do
# escritório. Pra trocar a senha de alguém, gera um novo hash (veja
# instruções) e troca só a variável de ambiente correspondente, sem
# precisar mexer em código nenhum.
USUARIOS = {
    "raquel": {
        "nome": "Raquel",
        "senha_hash": os.getenv("RAQUEL_SENHA_HASH"),
        "ativo": True,
    },
    "areudo": {
        "nome": "Areudo",
        "senha_hash": os.getenv("AREUDO_SENHA_HASH"),
        "ativo": True,
    },
}


def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    return pwd_context.verify(senha_plana, senha_hash)


def autenticar_usuario(username: str, senha: str):
    usuario = USUARIOS.get(username.lower())
    if not usuario or not usuario["ativo"] or not usuario["senha_hash"]:
        return None
    if not verificar_senha(senha, usuario["senha_hash"]):
        return None
    return {"username": username, "nome": usuario["nome"]}


def criar_access_token(dados: dict) -> str:
    payload = dados.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload["type"] = "access"
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def criar_refresh_token(dados: dict) -> str:
    payload = dados.copy()
    payload["exp"] = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload["type"] = "refresh"
    return jwt.encode(payload, REFRESH_SECRET_KEY, algorithm=ALGORITHM)


def usuario_atual(request: Request):
    """Lê o access token do cabeçalho Authorization: Bearer <token>.

    Antes lia de cookie — trocado porque frontend e backend ficam em
    domínios DIFERENTES no Railway, e cookie entre domínios diferentes
    é bloqueado por proteções de privacidade cada vez mais comuns nos
    navegadores (confirmado testando: o cookie nunca chegava de volta,
    mesmo com sameSite="none" configurado certo). Cabeçalho Authorization
    não depende de cookie nenhum, funciona igual em qualquer navegador.
    """
    erro = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autorizado",
    )
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise erro
    token = auth_header[len("Bearer "):]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise erro
        username = payload.get("username")
        if not username:
            raise erro
        return payload
    except JWTError:
        raise erro


def validar_refresh_token(token: str) -> dict:
    erro = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token inválido ou expirado",
    )
    if esta_revogado(token):
        raise erro
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise erro
        return payload
    except JWTError:
        raise erro


def revogar_refresh_token(token: str):
    """Guarda o refresh token numa lista negra até ele expirar sozinho."""
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        if exp:
            segundos_restantes = max(int(exp - datetime.utcnow().timestamp()), 1)
            conexao_redis.setex(f"revogado:{token}", segundos_restantes, "1")
    except JWTError:
        pass  # token já inválido, não precisa revogar


def esta_revogado(token: str) -> bool:
    return conexao_redis.exists(f"revogado:{token}") == 1