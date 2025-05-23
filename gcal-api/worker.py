import os
from typing import Dict, Any
from shared import (
    RedisQueueWorker,
    GOOGLE_API_QUEUE_NAME,
    GoogleAPIReq,
    RESPONSE_PREFIX,
)
from gcalendar import GoogleCalendar


def process_google_calendar_task(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Przetwarza zadanie Google Calendar API.

    Args:
        data: Słownik z danymi zadania

    Returns:
        Słownik z wynikiem przetwarzania
    """
    try:
        # Walidacja danych wejściowych przy użyciu Pydantic
        model = GoogleAPIReq.model_validate(data)
        print(f"📅 Przetwarzam zadanie Google Calendar: {len(model.events)} wydarzeń")

        # Utworzenie klienta Google Calendar
        google_client = GoogleCalendar(model.token)

        # Dodanie wydarzeń do kalendarza
        result = google_client.add_events(model.events)

        # Przygotowanie odpowiedzi
        response_data = {
            "status": "success",
            "message": "Wydarzenia zostały dodane do kalendarza",
            "events_count": len(model.events),
            "result": result if result else "OK",
        }

        print(f"✅ Pomyślnie dodano {len(model.events)} wydarzeń do kalendarza")
        return response_data

    except Exception as e:
        # W przypadku błędu zwracamy informację o błędzie
        error_response = {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__,
        }
        print(f"❌ Błąd podczas przetwarzania zadania Google Calendar: {e}")
        return error_response


def main():
    """Główna funkcja uruchamiająca worker Google Calendar"""

    # Konfiguracja
    REDIS_URL = os.environ.get("REDIS_URL", "redis://autocal-redis:6379")
    WORKER_NAME = "google-calendar-worker"

    print(f"🚀 Inicjalizacja {WORKER_NAME}...")

    try:
        # Utworzenie worker'a
        worker = RedisQueueWorker(
            name=WORKER_NAME, redis_url=REDIS_URL, queue_name=GOOGLE_API_QUEUE_NAME
        )

        print("📡 Sprawdzanie połączenia z Redis...")
        if not worker.health_check():
            print("❌ Brak połączenia z Redis")
            return

        print("✅ Połączenie z Redis OK")
        print(f"🎯 Nasłuchuję kolejki: '{GOOGLE_API_QUEUE_NAME}'")
        print(
            f"📤 Odpowiedzi będą wysyłane do: '{RESPONSE_PREFIX}{GOOGLE_API_QUEUE_NAME}'"
        )
        print("⚡ Worker gotowy do pracy. Naciśnij Ctrl+C aby zatrzymać.")

        # Uruchomienie nasłuchiwania kolejki
        worker.listen(process_google_calendar_task)

    except Exception as e:
        print(f"❌ Błąd podczas inicjalizacji worker'a: {e}")
        return


if __name__ == "__main__":
    main()
