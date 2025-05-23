import os
import uuid
import redis
import json

from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from planvalidation import JsonValidator, BadJsonFormatException
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta

from shared import GoogleAPIReq
from shared.types import ReqType

app = FastAPI()
validator = JsonValidator()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://autocal-mongo:27017/")
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client["autocal"]
configurations = db["configurations"]

REDIS_URL = os.getenv("REDIS_URL", "redis://autocal-redis:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL)

DATA_QUEUE_NAME = "data_queue"
GOOGLE_API_QUEUE_NAME = "google_api_queue"

RP = "RES:"


@app.post("/export")
async def handle_export(request: dict = Body(...)):
    try:
        config_id = request.get("config_id")
        offset = request.get("offset", 0)  # Domyślnie aktualny tydzień

        if not config_id:
            raise HTTPException(status_code=400, detail="config_id is required")

        print(f"📅 Eksport dla config_id: {config_id}, offset: {offset}")

        entry = configurations.find_one(
            {"_id": config_id}, {"_id": 0, "tk": 1, "schedule": 1, "timetable": 1}
        )
        if entry is None:
            raise HTTPException(status_code=404, detail="Configuration not found")

        # Obliczenie zakresu dat na podstawie offsetu
        today = datetime.today()
        start_of_week = today - timedelta(
            days=today.weekday()
        )  # Poniedziałek aktualnego tygodnia
        target_start = start_of_week + timedelta(
            weeks=offset
        )  # Przesunięcie o offset tygodni
        target_end = target_start + timedelta(days=4)  # Piątek (0-4 = Pon-Pią)

        # Formatowanie dat
        start_date = target_start.strftime("%d.%m.%Y")
        end_date = target_end.strftime("%d.%m.%Y")

        print(f"📊 Zakres dat: {start_date} - {end_date}")

        data_to_prepare = {
            "schedule": entry["schedule"],
            "timetable": entry["timetable"],
            "start_date": start_date,
            "end_date": end_date,
            "offset": offset,
        }

        # Umieść zadanie w kolejce data-prepare
        redis_client.rpush(DATA_QUEUE_NAME, json.dumps(data_to_prepare))
        print("📤 Wysłano zadanie do data-prepare")

        # Oczekiwanie na odpowiedź z data-prepare
        response = redis_client.blpop(RP + DATA_QUEUE_NAME, timeout=30)

        if response is None:
            raise HTTPException(
                status_code=408, detail="Timeout waiting for data preparation"
            )

        prepared_data = json.loads(response[1])
        print(
            f"📥 Otrzymano przygotowane dane: {len(prepared_data.get('events', []))} wydarzeń"
        )

        # Przygotowanie zadania dla Google Calendar API
        google_req = GoogleAPIReq(
            token=entry["tk"], events=prepared_data.get("events", [])
        )

        # Wysłanie do Google Calendar worker
        redis_client.rpush(GOOGLE_API_QUEUE_NAME, google_req.model_dump_json())
        print("📤 Wysłano zadanie do Google Calendar")

        # Oczekiwanie na odpowiedź z Google Calendar
        google_response = redis_client.blpop(RP + GOOGLE_API_QUEUE_NAME, timeout=360)

        if google_response is None:
            raise HTTPException(
                status_code=408, detail="Timeout waiting for Google Calendar export"
            )

        final_result = json.loads(google_response[1])
        print(f"✅ Eksport zakończony: {final_result}")

        return {
            "status": "success",
            "message": f"Plan został wygenerowany dla tygodnia {start_date} - {end_date}",
            "offset": offset,
            "date_range": {"start": start_date, "end": end_date},
            "events_count": len(prepared_data.get("events", [])),
            "google_calendar_result": final_result,
        }

    except Exception as e:
        print(f"❌ Błąd podczas eksportu: {e}")
        raise HTTPException(500, f"Server error: {str(e)}")


@app.post("/config")
async def handle_config(
    token: UploadFile = File(..., description="Plik google auth"),
    schedule: UploadFile = File(..., description="Plik terminarza wydziałowego"),
    timetable: UploadFile = File(..., description="Plik planu studenta"),
):
    try:
        schedule_data = validator.parse_schedule(schedule.file.read())
        timetable_data = validator.parse_timetable(timetable.file.read())

        config_id = str(uuid.uuid4())

        document = {
            "_id": config_id,
            "tk": token.file.read(),
            "schedule": schedule_data,
            "timetable": timetable_data,
            "created_at": datetime.now(timezone.utc),
        }

        result = configurations.insert_one(document)

        if not result.acknowledged:
            raise HTTPException(500, "Database write failed")

        return {"status": "success", "config_id": config_id}

    except BadJsonFormatException as e:
        raise HTTPException(500, f"Server error: {str(e)}")


@app.get("/health")
def health_check():
    return {"status": "ok"}
