import os
from redis import Redis
from redis.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError, TimeoutError
from rq import Queue

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


conexao_redis = Redis.from_url(
    REDIS_URL,
    socket_keepalive=True,
    socket_connect_timeout=10,
    retry_on_timeout=True,
    retry_on_error=[ConnectionError, TimeoutError],
    retry=Retry(ExponentialBackoff(), retries=5),
    health_check_interval=30,
)

fila_processamento = Queue("processamento", connection=conexao_redis)