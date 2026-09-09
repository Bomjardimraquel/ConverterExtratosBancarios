import time
from utils.fila import conexao_redis
from rq import SimpleWorker

if __name__ == "__main__":

    while True:
        try:
            worker = SimpleWorker(["processamento"], connection=conexao_redis)
            worker.work()
        except Exception as e:
            print(f"Worker caiu ({e}), tentando de novo em 5s...")
            time.sleep(5)