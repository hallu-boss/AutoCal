import requests

def config():
    schedule_path = 'data/schedule.json'
    timetable_path = 'data/timetable.json'

    with open(schedule_path, 'r') as sf, open(timetable_path, 'r') as tf:
        files = {
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
    data = { "config_id": "f151f166-936a-44b9-97a1-935b4e4c8218" }
    headers = { "Content-Type": "application/json" }

    return requests.post(url, json=data, headers=headers)

if __name__ == '__main__':
    res = export()

    if res.status_code == 200:
        print("✅ Sukces!")
        print(f"odpowiedź: {res.json()}")
    else:
        print(f"❌ Błąd: {res.json().get('detail')}")

    print(res)