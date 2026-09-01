from fastapi import APIRouter, HTTPException, status, Response, Request
from pydantic import BaseModel
from utils.auth import (
    autenticar_usuario, criar_access_token, criar_refresh_token,
    validar_refresh_token, REFRESH_TOKEN_EXPIRE_DAYS, PRODUCAO
)
from utils.fila import conexao_redis

router = APIRouter()

MAX_TENTATIVAS = 5
JANELA_BLOQUEIO_SEGUNDOS = 15 * 60  # 15 minutos


def _checar_rate_limit(username: str):
    chave = f"login_tentativas:{username.lower()}"
    tentativas = conexao_redis.get(chave)
    if tentativas and int(tentativas) >= MAX_TENTATIVAS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente em alguns minutos.",
        )


def _registrar_tentativa_falha(username: str):
    chave = f"login_tentativas:{username.lower()}"
    tentativas = conexao_redis.incr(chave)
    if tentativas == 1:
        conexao_redis.expire(chave, JANELA_BLOQUEIO_SEGUNDOS)


def _limpar_tentativas(username: str):
    conexao_redis.delete(f"login_tentativas:{username.lower()}")


class LoginRequest(BaseModel):
    username: str
    senha: str


def _set_cookies(response: Response, username: str, nome: str):
    """Define os cookies HTTP-only de access e refresh token."""
    access = criar_access_token({"username": username, "nome": nome})
    refresh = criar_refresh_token({"username": username, "nome": nome})

    samesite_valor = "none" if PRODUCAO else "lax"

    # Access token — 15 minutos
    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=PRODUCAO,
        samesite=samesite_valor,
        max_age=15 * 60,
    )
    # Refresh token — 7 dias
    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        secure=PRODUCAO,
        samesite=samesite_valor,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )
    return nome


@router.post("/login")
def login(dados: LoginRequest, response: Response):
    _checar_rate_limit(dados.username)

    usuario = autenticar_usuario(dados.username, dados.senha)
    if not usuario:
        _registrar_tentativa_falha(dados.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
        )
    _limpar_tentativas(dados.username)
    _set_cookies(response, usuario["username"], usuario["nome"])
    return {"nome": usuario["nome"], "username": usuario["username"]}


@router.post("/refresh")
def refresh(request: Request, response: Response):
    """Gera novo access token usando o refresh token."""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token não encontrado")
    payload = validar_refresh_token(token)
    _set_cookies(response, payload["username"], payload["nome"])
    return {"ok": True}


@router.post("/logout")
def logout(request: Request, response: Response):
    from utils.auth import revogar_refresh_token
    token = request.cookies.get("refresh_token")
    if token:
        revogar_refresh_token(token)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    from utils.auth import usuario_atual
    usuario = usuario_atual(request)
    return {"username": usuario["username"], "nome": usuario["nome"]}
