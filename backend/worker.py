from utils.fila import conexao_redis
from rq import Worker

if __name__ == "__main__":
    worker = Worker(["processamento"], connection=conexao_redis)
    worker.work()