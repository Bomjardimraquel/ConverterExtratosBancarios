from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel
from utils.auth import (
    autenticar_usuario, criar_access_token, criar_refresh_token,
    validar_refresh_token
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


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str = None


# Token agora vai no CORPO da resposta (não mais em cookie) — o frontend
# guarda em localStorage e manda em todo pedido seguinte pelo cabeçalho
# "Authorization: Bearer <token>". Ver utils/auth.py pro motivo da troca.
@router.post("/login")
def login(dados: LoginRequest):
    _checar_rate_limit(dados.username)

    usuario = autenticar_usuario(dados.username, dados.senha)
    if not usuario:
        _registrar_tentativa_falha(dados.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
        )
    _limpar_tentativas(dados.username)

    access = criar_access_token({"username": usuario["username"], "nome": usuario["nome"]})
    refresh = criar_refresh_token({"username": usuario["username"], "nome": usuario["nome"]})
    return {
        "nome": usuario["nome"],
        "username": usuario["username"],
        "access_token": access,
        "refresh_token": refresh,
    }


@router.post("/refresh")
def refresh(dados: RefreshRequest):
    """Gera novo access token (e novo refresh token) usando o refresh
    token que o frontend manda explicitamente no corpo do pedido."""
    payload = validar_refresh_token(dados.refresh_token)
    access = criar_access_token({"username": payload["username"], "nome": payload["nome"]})
    novo_refresh = criar_refresh_token({"username": payload["username"], "nome": payload["nome"]})
    return {"access_token": access, "refresh_token": novo_refresh}


@router.post("/logout")
def logout(dados: LogoutRequest):
    from utils.auth import revogar_refresh_token
    if dados.refresh_token:
        revogar_refresh_token(dados.refresh_token)
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    from utils.auth import usuario_atual
    usuario = usuario_atual(request)
    return {"username": usuario["username"], "nome": usuario["nome"]}