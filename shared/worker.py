from typing import Final

import redis
import json


RESPONSE_PREFIX: Final[str] = "RES:"

class RedisQueueWorker:
    def __init__(self, name:str, *, redis_url:str, queue_name:str):
        self.name = name
        self.queue_name = queue_name

        try:
            self.redis_client = redis.Redis.from_url(redis_url)

        except redis.exceptions.ConnectionError as e:
            print(f"❌ Nie można połączyć się z Redis: {str(e)}")

    def listen(self, func):
        print(f"🚀 Worker {self.name} uruchomiony. Nasłuchuję kolejki '{self.queue_name}'...")

        try:
            while True:
                queue_node = self.redis_client.blpop(self.queue_name, timeout=10)

                if queue_node is None:
                    print("🕒 Brak danych w kolejce...")
                    continue

                queue_data = queue_node[1]
                if queue_data is None:
                    continue

                try:
                    data = json.loads(queue_data)

                except json.decoder.JSONDecodeError as e:
                    print(f"⚠️ Błąd dekodowania JSON: {e}")
                    continue

                try:
                    res = func(data)
                    self.redis_client.rpush(RESPONSE_PREFIX + self.queue_name, json.dumps(res))

                except Exception as e:
                    print(f"❌ Błąd podczas wykonywania funkcji przetwarzającej dane: {e}")

        except Exception as e:
            print(f"❌ Nieoczekiwany błąd: {str(e)}")
