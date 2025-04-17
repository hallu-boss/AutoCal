import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from planvalidation import JsonValidator, BadJsonFormatException
from pymongo import MongoClient

app = FastAPI()
validator = JsonValidator()
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://root:example@autocal-mongo:27017")
client = MongoClient(MONGODB_URI)
db = client.autocal
configurations = db.configurations

@app.post("/config")
async def handle_config(
        schedule: UploadFile = File(..., description="Plik terminarza wydziałowego"),
        timetable: UploadFile = File(..., description="Plik planu studenta")
):
    try:
        schedule_data = validator.parse_schedule(schedule.file.read())
        timetable_data = validator.parse_timetable(timetable.file.read())

        print(schedule_data)
        print(timetable_data)
    except BadJsonFormatException as e:
        raise HTTPException(500, f"Server error: {str(e)}")

@app.get("/health")
def health_check():
    return {"status": "ok"}