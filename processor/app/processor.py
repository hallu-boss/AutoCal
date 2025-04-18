import os
import uuid
import redis
import json

from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from planvalidation import JsonValidator, BadJsonFormatException
from pymongo import MongoClient
from datetime import datetime, timezone

app = FastAPI()
validator = JsonValidator()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://autocal-mongo:27017/")
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client["autocal"]
configurations = db["configurations"]

REDIS_URL = os.getenv("REDIS_URL", "redis://autocal-redis:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL)

# Google Delegate Task Queue
gtq_name = "google_task_queue"

# Google Response Queue Prefix (dynamic per config_id)
grq_prefix = "google_response:"

@app.post("/export")
async def handle_export(config_id: str = Body(..., embed=True)):
    try:
        entry = configurations.find_one(
            {"_id": config_id},
            {"_id": 0, "schedule": 1, "timetable": 1}
        )
        if entry is None:
            raise HTTPException(status_code=404, detail="Configuration not found")

        task = {
            "config_id": config_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }

        # Umieść zadanie w kolejce
        redis_client.rpush(gtq_name, json.dumps(task))

        # Kolejka odpowiedzi dla danego config_id
        response_queue = f"{grq_prefix}{config_id}"

        # Oczekiwanie na odpowiedź maksymalnie 15 sekund
        response = redis_client.blpop(response_queue, timeout=15)

        if response is None:
            raise HTTPException(504, "Timeout waiting for export result")

        _, data = response
        result = json.loads(data)

        return {"status": "success", "result": result}

    except Exception as e:
        raise HTTPException(500, f"Server error: {str(e)}")

@app.post("/config")
async def handle_config(
        schedule: UploadFile = File(..., description="Plik terminarza wydziałowego"),
        timetable: UploadFile = File(..., description="Plik planu studenta")
):
    try:
        schedule_data = validator.parse_schedule(schedule.file.read())
        timetable_data = validator.parse_timetable(timetable.file.read())

        config_id = str(uuid.uuid4())
        document = {
            "_id": config_id,
            "schedule": schedule_data,
            "timetable": timetable_data,
            "created_at": datetime.now(timezone.utc)
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
