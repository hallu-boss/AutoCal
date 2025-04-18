import json
import os
import redis
import time  # do symulacji pracy

def main():
    REDIS_URL = os.environ.get("REDIS_URL", "redis://autocal-redis:6379")
    task_queue = "google_task_queue"  # musi być zgodne z FastAPI
    response_prefix = "google_response:"

    print(f"🚀 Worker Google Calendar uruchomiony. Nasłuchuję kolejki '{task_queue}'...")

    try:
        red = redis.Redis.from_url(REDIS_URL)

        while True:
            task = red.blpop(task_queue, timeout=10)

            if task:
                _, task_json = task
                task_data = json.loads(task_json)

                config_id = task_data.get("config_id")
                if not config_id:
                    print("⚠️ Brak config_id w zadaniu, pomijam.")
                    continue

                print(f"📝 Przetwarzanie config_id={config_id}...")

                # (opcjonalnie) symulacja eksportu
                time.sleep(2)

                # przykładowa odpowiedź
                response_data = {
                    "config_id": config_id,
                    "status": "done",
                    "export_url": f"https://example.com/export/{config_id}.ics"
                }

                # wyślij odpowiedź do dynamicznej kolejki
                response_queue = f"{response_prefix}{config_id}"
                red.rpush(response_queue, json.dumps(response_data))

                print(f"✅ Zakończono eksport dla {config_id}, wysłano odpowiedź.")
            else:
                print("🕒 Brak zadań w kolejce...")

    except redis.ConnectionError as e:
        print(f"❌ Nie można połączyć się z Redis: {str(e)}")
    except KeyboardInterrupt:
        print("\n🛑 Zatrzymywanie workera...")
    except Exception as e:
        print(f"❌ Nieoczekiwany błąd: {str(e)}")

if __name__ == "__main__":
    main()
