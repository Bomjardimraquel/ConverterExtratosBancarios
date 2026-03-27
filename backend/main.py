from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.extrato import router as extrato_router

app = FastAPI(title="Conversor de Extratos Bancários", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extrato_router, prefix="/api")

@app.get("/")
def root():
    return {"status": "ok", "message": "Conversor de Extratos Bancários"}
