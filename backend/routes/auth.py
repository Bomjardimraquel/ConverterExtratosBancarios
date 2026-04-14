from fastapi import APIRouter, HTTPException, status, Response, Request
from pydantic import BaseModel
from utils.auth import (
    autenticar_usuario, criar_access_token, criar_refresh_token,
    validar_refresh_token, REFRESH_TOKEN_EXPIRE_DAYS
)

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    senha: str


def _set_cookies(response: Response, username: str, nome: str):
    """Define os cookies HTTP-only de access e refresh token."""
    access = criar_access_token({"username": username, "nome": nome})
    refresh = criar_refresh_token({"username": username, "nome": nome})

    # Access token — 15 minutos
    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=False,   # Mude para True em produção com HTTPS
        samesite="lax",
        max_age=15 * 60,
    )
    # Refresh token — 7 dias
    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        secure=False,   # Mude para True em produção com HTTPS
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )
    return nome


@router.post("/login")
def login(dados: LoginRequest, response: Response):
    usuario = autenticar_usuario(dados.username, dados.senha)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
        )
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
def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    from utils.auth import usuario_atual
    usuario = usuario_atual(request)
    return {"username": usuario["username"], "nome": usuario["nome"]}