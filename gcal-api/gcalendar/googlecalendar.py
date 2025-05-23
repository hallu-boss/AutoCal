import json
from pathlib import Path
from typing import Final, List
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from zoneinfo import ZoneInfo
from datetime import datetime
from shared import CalendarEvent, WARSAW_TZ


class GCException(Exception):
    def __init__(self, message):
        self.message = message


def assign_to(attr_name):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            if result:
                setattr(self, attr_name, result)
            return result

        return wrapper

    return decorator


class GoogleCalendar:
    SCOPES: Final[list] = ["https://www.googleapis.com/auth/calendar"]
    credentials_name: Final[str] = "credentials.json"
    calendar_name: Final[str] = "AutoCal"
    timezone: Final[ZoneInfo] = WARSAW_TZ

    @staticmethod
    def create_credentials():
        credentials_path = Path(__file__).parent / GoogleCalendar.credentials_name

        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path), GoogleCalendar.SCOPES
        )
        creds = flow.run_local_server(port=0)

        return creds

    def __init__(self, token: str):
        self.creds = Credentials.from_authorized_user_info(
            json.loads(token), GoogleCalendar.SCOPES
        )
        self.calendar_id = None

        if not self.creds.valid:
            if self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                raise GCException("Google Calendar credentials not available")

        self.service = build("calendar", "v3", credentials=self.creds)

    def _format_datetime(self, date_str: str, time_str: str) -> str:
        """
        Konwertuje datę i czas do formatu ISO 8601 wymaganego przez Google Calendar API

        Args:
            date_str: Data w formacie "DD.MM.YYYY"
            time_str: Czas w formacie "HH:MM"

        Returns:
            String w formacie ISO 8601: "YYYY-MM-DDTHH:MM:SS"
        """
        try:
            # Parsowanie daty DD.MM.YYYY
            date_obj = datetime.strptime(date_str, "%d.%m.%Y")
            # Parsowanie czasu HH:MM
            time_obj = datetime.strptime(time_str, "%H:%M").time()
            # Połączenie daty i czasu
            combined = datetime.combine(date_obj.date(), time_obj)
            # Zwrócenie w formacie ISO 8601
            return combined.strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError as e:
            print(f"❌ Błąd formatowania daty/czasu: {date_str} {time_str} - {e}")
            raise

    def _convert_event_data(self, event_data: dict) -> dict:
        """
        Konwertuje surowe dane wydarzenia do formatu Google Calendar API

        Args:
            event_data: Słownik z danymi wydarzenia z data-prepare

        Returns:
            Słownik w formacie Google Calendar API
        """
        try:
            # Formatowanie dat zgodnie z wymaganiami Google Calendar API
            start_datetime = self._format_datetime(
                event_data["date"], event_data["start_time"]
            )
            end_datetime = self._format_datetime(
                event_data["date"], event_data["end_time"]
            )

            # Przygotowanie wydarzenia dla Google Calendar API
            google_event = {
                "summary": event_data.get("title", "Zajęcia"),
                "description": event_data.get("description", ""),
                "start": {
                    "dateTime": start_datetime,
                    "timeZone": self.timezone.key,
                },
                "end": {
                    "dateTime": end_datetime,
                    "timeZone": self.timezone.key,
                },
            }

            # Dodanie lokalizacji jeśli istnieje
            if event_data.get("location"):
                google_event["location"] = event_data["location"]

            return google_event

        except Exception as e:
            print(f"❌ Błąd konwersji wydarzenia: {e}")
            raise

    @assign_to("calendar_id")
    def create_cal(self):
        cal_id = self.get_calendar_id()
        if cal_id:
            return cal_id

        calendar = {
            "summary": GoogleCalendar.calendar_name,
            "timeZone": GoogleCalendar.timezone.key,
        }

        req = self.service.calendars().insert(body=calendar)
        created_calendar = req.execute()

        return created_calendar["id"]

    @assign_to("calendar_id")
    def get_calendar_id(self):
        if self.calendar_id:
            return self.calendar_id

        calendars = self.service.calendarList().list().execute()
        for cal in calendars.get("items", []):
            if cal["summary"] == GoogleCalendar.calendar_name:
                return cal["id"]

        return None

    def get_events(self, start_date: datetime, end_date: datetime) -> List[dict]:
        cal_id = self.get_calendar_id()
        if not cal_id:
            raise GCException("Google Calendar does not exist")

        time_min = start_date.isoformat()
        time_max = end_date.isoformat()

        events_result = (
            self.service.events()
            .list(
                calendarId=cal_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        return events_result.get("items", [])

    def add_event(self, event: dict):
        """
        Dodaje pojedyncze wydarzenie do kalendarza

        Args:
            event: Może być gotowym obiektem Google Calendar API
                   lub surowymi danymi z data-prepare
        """
        # Sprawdź czy to surowe dane czy gotowy obiekt Google Calendar
        if "start" not in event or "end" not in event:
            # To są surowe dane - konwertuj je
            event = self._convert_event_data(event)

        return (
            self.service.events()
            .insert(calendarId=self.create_cal(), body=event)
            .execute()
        )

    def add_events(self, events: List[dict]) -> List[dict]:
        """
        Dodaje wiele wydarzeń do kalendarza

        Args:
            events: Lista wydarzeń (surowe dane lub gotowe obiekty Google Calendar)

        Returns:
            Lista wyników dla każdego wydarzenia
        """
        results = []

        for i, event_data in enumerate(events):
            try:
                print(
                    f"📅 Dodaję wydarzenie {i + 1}/{len(events)}: {event_data.get('title', 'Unknown')}"
                )

                # Konwersja surowych danych do formatu Google Calendar API
                if "start" not in event_data or "end" not in event_data:
                    google_event = self._convert_event_data(event_data)
                else:
                    google_event = event_data

                # Dodanie wydarzenia
                response = (
                    self.service.events()
                    .insert(calendarId=self.create_cal(), body=google_event)
                    .execute()
                )

                result = {
                    "status": "success",
                    "event_id": response.get("id"),
                    "event_title": event_data.get("title", "Zajęcia"),
                    "date": event_data.get("date"),
                    "start_time": event_data.get("start_time"),
                    "end_time": event_data.get("end_time"),
                }
                results.append(result)
                print(f"✅ Dodano: {event_data.get('title', 'Unknown')}")

            except HttpError as e:
                error_result = {
                    "status": "error",
                    "error": str(e),
                    "event": event_data,
                    "error_details": {
                        "reason": e.error_details[0].get("reason")
                        if e.error_details
                        else "unknown",
                        "message": e.error_details[0].get("message")
                        if e.error_details
                        else str(e),
                    },
                }
                results.append(error_result)
                print(
                    f"❌ Błąd HTTP dodawania wydarzenia '{event_data.get('title', 'Unknown')}': {e}"
                )

            except Exception as e:
                error_result = {
                    "status": "error",
                    "error": str(e),
                    "event": event_data,
                    "error_type": type(e).__name__,
                }
                results.append(error_result)
                print(f"❌ Nieoczekiwany błąd: {e}")

        # Podsumowanie
        success_count = sum(1 for r in results if r.get("status") == "success")
        error_count = len(results) - success_count

        print(f"📊 Podsumowanie: {success_count} sukcessów, {error_count} błędów")

        return results

    def health_check(self) -> bool:
        """Sprawdza czy połączenie z Google Calendar działa"""
        try:
            # Próba pobrania listy kalendarzy
            self.service.calendarList().list(maxResults=1).execute()
            print("✅ Połączenie z Google Calendar OK")
            return True
        except Exception as e:
            print(f"❌ Błąd połączenia z Google Calendar: {e}")
            return False

    def delete_event(self, event_id: str) -> bool:
        cal_id = self.get_calendar_id()
        if not cal_id:
            raise GCException("Google Calendar does not exist")

        try:
            self.service.events().delete(calendarId=cal_id, eventId=event_id).execute()

        except HttpError as error:
            raise GCException("Google Calendar API call failed") from error

        return True

    def delete_events(self, events: List[str]) -> List[bool]:
        cal_id = self.get_calendar_id()
        if not cal_id:
            raise GCException("Google Calendar does not exist")

        results = []

        for eid in events:
            try:
                self.service.events().delete(calendarId=cal_id, eventId=eid).execute()

                results.append(True)

            except HttpError as error:
                results.append({"error": str(error), "event": eid})

        return results
