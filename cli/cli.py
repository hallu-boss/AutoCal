import requests

def send_to_processor():
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

if __name__ == '__main__':
    res = send_to_processor()
    print(res)