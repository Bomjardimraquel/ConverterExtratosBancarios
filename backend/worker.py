from utils.fila import conexao_redis
from rq import SimpleWorker

if __name__ == "__main__":
    worker = SimpleWorker(["processamento"], connection=conexao_redis)
    worker.work()