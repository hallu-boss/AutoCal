import requests

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def register():
    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    credentials_path = "credentials.json"

    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
    creds = flow.run_local_server(port=0)

    with open('token.json', 'w') as token:
        token.write(creds.to_json())

def config():
    schedule_path = 'data/schedule.json'
    timetable_path = 'data/timetable.json'
    token_path = 'token.json'

    with open(schedule_path, 'r') as sf, open(timetable_path, 'r') as tf, open(token_path, 'r') as tkf:
        files = {
            'token': ('token.json', tkf, 'application/json'),
            'schedule': ('schedule.json', sf, 'application/json'),
            'timetable': ('timetable.json', tf, 'application/json')
        }

        return requests.post(
            'http://0.0.0.0:8000/config',
            files=files,
            timeout=10
        )

def export():
    url = 'http://0.0.0.0:8000/export'
    data = { "config_id": "569923a1-acde-4240-b2c9-794fff4948bb" }
    headers = { "Content-Type": "application/json" }

    return requests.post(url, json=data, headers=headers)

def endpoint_action(func):
    res = func()

    if res.status_code == 200:
        print("✅ Sukces!")
        print(f"odpowiedź: {res.json()}")
    else:
        print(f"❌ Błąd: {res.json().get('detail')}")

    print(res)

if __name__ == '__main__':
    # register()
    endpoint_action(export)