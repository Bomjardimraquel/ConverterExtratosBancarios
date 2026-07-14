from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from routes.extrato import router as extrato_router
from routes.auth import router as auth_router
from utils.auth import usuario_atual
from routes.modulo2 import router as modulo2_router

app = FastAPI(title="ExtratoConverter", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth")
app.include_router(extrato_router, prefix="/api", dependencies=[Depends(usuario_atual)])
app.include_router(modulo2_router, prefix="/api/modulo2", dependencies=[Depends(usuario_atual)])

@app.get("/")
def root():
    return {"status": "ok", "app": "ExtratoConverter"}