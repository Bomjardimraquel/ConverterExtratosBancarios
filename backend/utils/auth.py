from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from utils.fila import conexao_redis
import os

PRODUCAO = os.getenv("AMBIENTE") == "producao"

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
    """Lê o access token do cookie HTTP-only."""
    erro = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autorizado",
    )
    token = request.cookies.get("access_token")
    if not token:
        raise erro
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
        pass 


def esta_revogado(token: str) -> bool:
    return conexao_redis.exists(f"revogado:{token}") == 1
