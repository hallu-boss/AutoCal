from typing import Final
import redis
import json
import signal
import time

RESPONSE_PREFIX: Final[str] = "RES:"


class RedisQueueWorker:
    def __init__(self, name: str, *, redis_url: str, queue_name: str):
        self.name = name
        self.queue_name = queue_name
        self.running = True

        try:
            self.redis_client = redis.Redis.from_url(redis_url)
            # Test połączenia
            self.redis_client.ping()
            print("✅ Połączono z Redis")
        except redis.exceptions.ConnectionError as e:
            print(f"❌ Nie można połączyć się z Redis: {str(e)}")
            raise
        except Exception as e:
            print(f"❌ Błąd Redis: {str(e)}")
            raise

        # Rejestracja obsługi sygnałów
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Obsługa sygnałów przerwania"""
        signal_names = {signal.SIGINT: "SIGINT", signal.SIGTERM: "SIGTERM"}
        signal_name = signal_names.get(signum, f"Signal {signum}")

        print(
            f"\n🛑 Otrzymano sygnał {signal_name}. Zatrzymywanie worker'a '{self.name}'..."
        )
        self.running = False

    def stop(self):
        """Programowe zatrzymanie worker'a"""
        print(f"🛑 Zatrzymywanie worker'a '{self.name}'...")
        self.running = False

    def listen(self, func):
        """
        Nasłuchuje kolejki i przetwarza wiadomości.
        Używa blokującego blpop() zamiast aktywnego czekania.
        """
        print(
            f"🚀 Worker {self.name} uruchomiony. Nasłuchuję kolejki '{self.queue_name}'..."
        )

        try:
            while self.running:
                try:
                    # Blokujące pobranie z krótkim timeout dla sprawdzenia self.running
                    queue_node = self.redis_client.blpop(self.queue_name, timeout=1)

                    if queue_node is None:
                        # Timeout - sprawdź czy nadal działamy
                        continue

                    _, queue_data = queue_node

                    if queue_data is None:
                        continue

                    # Dekodowanie JSON
                    try:
                        data = json.loads(
                            queue_data.decode("utf-8")
                            if isinstance(queue_data, bytes)
                            else queue_data
                        )
                        print(f"📨 Otrzymano wiadomość: {data}")
                    except json.JSONDecodeError as e:
                        print(f"⚠️ Błąd dekodowania JSON: {e}")
                        print(f"Raw data: {queue_data}")
                        continue

                    # Przetwarzanie danych
                    try:
                        start_time = time.time()
                        result = func(data)
                        processing_time = time.time() - start_time

                        print(f"✅ Przetworzono w {processing_time:.2f}s")

                        # Wysłanie odpowiedzi do kolejki odpowiedzi
                        if result is not None:
                            response_queue = RESPONSE_PREFIX + self.queue_name
                            self.redis_client.rpush(response_queue, json.dumps(result))
                            print(f"📤 Wysłano odpowiedź do '{response_queue}'")

                    except Exception as e:
                        print(f"❌ Błąd podczas przetwarzania: {e}")

                        # Opcjonalnie: wysłanie błędu do kolejki odpowiedzi
                        error_response = {
                            "error": str(e),
                            "type": type(e).__name__,
                            "original_data": data,
                        }
                        response_queue = RESPONSE_PREFIX + self.queue_name
                        self.redis_client.rpush(
                            response_queue, json.dumps(error_response)
                        )

                except redis.exceptions.ConnectionError as e:
                    print(f"⚠️ Utracono połączenie z Redis: {e}")
                    print("🔄 Próba ponownego połączenia za 5 sekund...")
                    time.sleep(5)
                    try:
                        self.redis_client.ping()
                        print("✅ Ponownie połączono z Redis")
                    except:
                        print("❌ Nie udało się ponownie połączyć")

                except Exception as e:
                    print(f"❌ Nieoczekiwany błąd w pętli: {e}")
                    # Krótka pauza, aby uniknąć szybkiej pętli błędów
                    time.sleep(1)

        except KeyboardInterrupt:
            print("\n🛑 Przerwano przez użytkownika")
        finally:
            print(f"🏁 Worker '{self.name}' zakończył pracę")

    def health_check(self) -> bool:
        """Sprawdza czy połączenie z Redis działa"""
        try:
            self.redis_client.ping()
            return True
        except:
            return False
