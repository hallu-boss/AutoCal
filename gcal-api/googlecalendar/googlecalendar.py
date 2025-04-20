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

        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), GoogleCalendar.SCOPES)
        creds = flow.run_local_server(port=0)

        return creds

    def __init__(self, token:str):
        self.creds = Credentials.from_authorized_user_info(json.loads(token), GoogleCalendar.SCOPES)
        self.calendar_id = None

        if not self.creds.valid:
            if self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                raise GCException("Google Calendar credentials not available")

        self.service = build("calendar", "v3", credentials=self.creds)

    @assign_to('calendar_id')
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

        return created_calendar['id']

    @assign_to('calendar_id')
    def get_calendar_id(self):
        if self.calendar_id:
            return self.calendar_id

        calendars = self.service.calendarList().list().execute()
        for cal in calendars.get('items', []):
            if cal['summary'] == GoogleCalendar.calendar_name:
                return cal['id']

        return None

    def get_events(self, start_date: datetime, end_date: datetime) -> List[dict]:
        cal_id = self.get_calendar_id()
        if not cal_id:
            raise GCException("Google Calendar does not exist")

        time_min = start_date.isoformat()
        time_max = end_date.isoformat()

        events_result = self.service.events().list(
            calendarId=cal_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        return events_result.get('items', [])

    def add_event(self, event: CalendarEvent):
        return self.service.events().insert(
            calendarId=self.create_cal(),
            body=event.to_dict()
        ).execute()

    def add_events(self, events: List[CalendarEvent]) -> List[dict]:
        results = []

        for event in events:
            try:
                response = self.add_event(event)
                results.append(response)
            except HttpError as e:
                results.append({
                    "error": str(e),
                    "event": event.to_dict()
                })

        return results

    def delete_event(self, event_id: str) -> bool:
        cal_id = self.get_calendar_id()
        if not cal_id:
            raise GCException("Google Calendar does not exist")

        try:
            self.service.events().delete(
                calendarId=cal_id,
                eventId=event_id
            ).execute()

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
                self.service.events().delete(
                    calendarId=cal_id,
                    eventId=eid
                ).execute()

                results.append(True)

            except HttpError as error:
                results.append({
                    "error": str(error),
                    "event": eid
                })

        return results