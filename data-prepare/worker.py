from datetime import datetime, timedelta
from shared import (
    RedisQueueWorker,
    DATA_QUEUE_NAME,
    WEEKS_HEADERS,
    WEEK_DAYS_HEADERS,
    WARSAW_TZ,
    CalendarEvent,
)


def get_work_week_days_in_range(start_date_str: str, end_date_str: str):
    """
    Zwraca dni robocze w podanym zakresie dat.

    Args:
        start_date_str: Data początkowa w formacie "DD.MM.YYYY"
        end_date_str: Data końcowa w formacie "DD.MM.YYYY"

    Returns:
        Lista dat w formacie "DD.MM.YYYY"
    """
    start_date = datetime.strptime(start_date_str, "%d.%m.%Y")
    end_date = datetime.strptime(end_date_str, "%d.%m.%Y")

    days = []
    current_date = start_date

    while current_date <= end_date:
        # Tylko dni robocze (0=poniedziałek, 4=piątek)
        if current_date.weekday() < 5:
            days.append(current_date.strftime("%d.%m.%Y"))
        current_date += timedelta(days=1)

    return days


def prepare(data):
    """
    Przygotowuje wydarzenia kalendarzowe na podstawie harmonogramu i planu zajęć

    Args:
        data: Słownik z kluczami:
            - schedule: harmonogram tygodni
            - timetable: plan zajęć
            - start_date: data początkowa
            - end_date: data końcowa
            - offset: przesunięcie tygodniowe

    Returns:
        Słownik z wydarzeniami w formacie Google Calendar API
    """
    schedule = data.get("schedule")
    timetable = data.get("timetable")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    offset = data.get("offset", 0)

    if not all([schedule, timetable, start_date, end_date]):
        print("❌ Brak wymaganych danych")
        return {"error": "Missing required data", "events": []}

    print(
        f"📊 Przetwarzanie danych dla zakresu: {start_date} - {end_date} (offset: {offset})"
    )

    # Pobierz dni robocze w podanym zakresie
    dates = get_work_week_days_in_range(start_date, end_date)
    print(f"📅 Dni do przetworzenia: {dates}")

    # Przygotowanie mapowania tygodni
    weeks = {k: v for k, v in schedule.items() if k != "year"}
    trans_weeks = {day: -1 for day in WEEK_DAYS_HEADERS}

    # Mapowanie dat na tygodnie w harmonogramie
    for day_idx, date in enumerate(dates):
        if day_idx >= len(WEEK_DAYS_HEADERS):  # Maksymalnie 5 dni roboczych
            break

        day_name = WEEK_DAYS_HEADERS[day_idx]

        # Znajdź w którym tygodniu harmonogramu jest ta data
        for week_key, week_dates in weeks.items():
            if date in week_dates:
                # Znajdź indeks tygodnia w WEEKS_HEADERS
                try:
                    week_number = WEEKS_HEADERS.index(week_key) + 1
                    trans_weeks[day_name] = week_number
                    print(
                        f"📍 {date} ({day_name}) -> tydzień {week_key} (nr {week_number})"
                    )
                    break
                except ValueError:
                    print(f"⚠️ Nieznany klucz tygodnia: {week_key}")

    print(f"🗓️ Mapowanie dni na tygodnie: {trans_weeks}")

    # Generowanie wydarzeń
    calendar_events = []
    events_by_date = {}

    for date, (day_name, week_number) in zip(dates, trans_weeks.items()):
        if week_number == -1:  # Brak zajęć w tym dniu
            print(f"⏭️ Brak zajęć dla {date} ({day_name})")
            continue

        # Pobierz plan zajęć dla tego dnia tygodnia
        day_timetable = timetable.get(day_name, [])
        day_events = []

        print(f"🔍 Sprawdzam zajęcia dla {date} ({day_name}), tydzień {week_number}")

        for event_data in day_timetable:
            # Sprawdź czy wydarzenie ma miejsce w tym tygodniu
            occurrences = event_data.get("occurrences", [])

            if week_number in occurrences:
                print(
                    f"  ✅ Zajęcia: {event_data.get('title', 'Unknown')} ({event_data.get('time', {}).get('start', '')} - {event_data.get('time', {}).get('end', '')})"
                )

                try:
                    # Użyj CalendarEvent do konwersji
                    calendar_event = CalendarEvent.from_dict(
                        event_data, date=date, timezone=WARSAW_TZ
                    )

                    # Konwertuj do formatu Google Calendar API
                    google_event = calendar_event.to_dict()
                    calendar_events.append(google_event)
                    day_events.append(event_data)

                except Exception as e:
                    print(f"❌ Błąd konwersji wydarzenia: {e}")
                    print(f"   Dane wydarzenia: {event_data}")
            else:
                print(
                    f"  ⏭️ Pomijam: {event_data.get('title', 'Unknown')} (występuje w tygodniach: {occurrences})"
                )

        if day_events:
            events_by_date[date] = day_events

    print(
        f"✅ Wygenerowano {len(calendar_events)} wydarzeń dla {len(events_by_date)} dni"
    )

    # Szczegółowe podsumowanie
    for date, events in events_by_date.items():
        print(f"📅 {date}: {len(events)} zajęć")
        for event in events:
            time_info = event.get("time", {})
            print(
                f"   - {event.get('title', 'Unknown')} ({time_info.get('start', '')} - {time_info.get('end', '')})"
            )

    return {
        "status": "success",
        "events": calendar_events,  # Już w formacie Google Calendar API
        "summary": {
            "date_range": f"{start_date} - {end_date}",
            "total_events": len(calendar_events),
            "days_with_events": len(events_by_date),
            "offset": offset,
        },
    }


if __name__ == "__main__":
    worker = RedisQueueWorker(
        "Data Prepare",
        redis_url="redis://autocal-redis:6379",
        queue_name=DATA_QUEUE_NAME,
    )
    worker.listen(prepare)
