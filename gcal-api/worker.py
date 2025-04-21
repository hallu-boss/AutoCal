import json
import os
import redis

from shared import GOOGLE_API_QUEUE_NAME, GoogleAPIReq, RESPONSE_PREFIX
from gcalendar import GoogleCalendar


def main():
    REDIS_URL = os.environ.get("REDIS_URL", "redis://autocal-redis:6379")
    task_queue = "google_task_queue"  # musi być zgodne z FastAPI

    print(f"🚀 Worker Google Calendar uruchomiony. Nasłuchuję kolejki '{task_queue}'...")

    try:
        red = redis.Redis.from_url(REDIS_URL)

        while True:
            task = red.lpop(GOOGLE_API_QUEUE_NAME)

            if task:
                model = GoogleAPIReq.model_validate_json(task)

                print(model)

                google_client = GoogleCalendar(model.token)
                google_client.add_events(model.events)

                # przykładowa odpowiedź
                response_data = {"status": "done"}

                # wyślij odpowiedź do dynamicznej kolejki
                response_queue = f"{RESPONSE_PREFIX}{GOOGLE_API_QUEUE_NAME}"
                red.rpush(response_queue, json.dumps(response_data))

                print(f"✅ Zakończono eksport, wysłano odpowiedź.")
            # else:
            #     print("🕒 Brak zadań w kolejce...")

    except redis.ConnectionError as e:
        print(f"❌ Nie można połączyć się z Redis: {str(e)}")
    except KeyboardInterrupt:
        print("\n🛑 Zatrzymywanie workera...")
    except Exception as e:
        print(f"❌ Nieoczekiwany błąd: {str(e)}")

if __name__ == "__main__":
    main()
