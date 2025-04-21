from datetime import datetime
from enum import Enum
from typing import Optional
from zoneinfo import ZoneInfo
from pydantic import BaseModel

class CalendarEvent(BaseModel):
    summary: str
    description: str
    start_time: datetime
    end_time: datetime
    timezone: ZoneInfo

    @classmethod
    def from_dict(cls, data: dict, *, date: str, timezone: ZoneInfo) -> "CalendarEvent":
        str_st = data["time"]["start"]
        str_ed = data["time"]["end"]
        stime = datetime.strptime(date + " " + str_st, "%d.%m.%Y %H:%M")
        etime = datetime.strptime(date + " " + str_ed, "%d.%m.%Y %H:%M")
        return cls(
            summary=data['title'],
            description=data['type'],
            start_time=stime,
            end_time=etime,
            timezone=timezone,
        )

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

class ReqType(Enum):
    REGISTER = "REGISTER"
    EXPORT = "EXPORT"

class GoogleAPIReq(BaseModel):
    token: str
    events: list
