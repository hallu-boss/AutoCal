from datetime import datetime
from zoneinfo import ZoneInfo
from pydantic import BaseModel

class CalendarEvent(BaseModel):
    summary: str
    description: str
    start_time: datetime
    end_time: datetime
    timezone: ZoneInfo

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "description": self.description,
            "start": {
                "dateTime": self.start_time.isoformat(),
                "timeZone": self.timezone.key,
            },
            "end": {
                "dateTime": self.end_time.isoformat(),
                "timeZone": self.timezone.key,
            }
        }