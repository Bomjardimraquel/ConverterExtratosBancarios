import os
from redis import Redis
from rq import Queue

# ── Conexão com o Redis ──────────────────────────────────────────────────────
# Local (rodando via Docker): "redis://localhost:6379"
# No Railway: o serviço de Redis expõe uma variável de ambiente própria
# (geralmente REDIS_URL) — configure-a nas variáveis do serviço do backend.
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

conexao_redis = Redis.from_url(REDIS_URL)

# Fila única de processamento. Se no futuro quiser separar prioridades
# (ex: extratos grandes vs pequenos), dá pra criar outra Queue com nome
# diferente reaproveitando a mesma conexao_redis.
fila_processamento = Queue("processamento", connection=conexao_redis)