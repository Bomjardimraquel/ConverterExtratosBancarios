from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import os
from routes.extrato import router as extrato_router
from routes.auth import router as auth_router
from utils.auth import usuario_atual
from routes.modulo2 import router as modulo2_router

app = FastAPI(title="Concilia", version="1.0.0")

origens_permitidas = ["http://localhost:3000", "http://127.0.0.1:3000"]
frontend_url_producao = os.getenv("FRONTEND_URL")
if frontend_url_producao:
    origens_permitidas.append(frontend_url_producao)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origens_permitidas,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth")
app.include_router(extrato_router, prefix="/api", dependencies=[Depends(usuario_atual)])
app.include_router(modulo2_router, prefix="/api/modulo2", dependencies=[Depends(usuario_atual)])

@app.get("/")
def root():
    return {"status": "ok", "app": "Concilia"}
