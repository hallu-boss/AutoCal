from datetime import datetime, timedelta
from shared import RedisQueueWorker, DATA_QUEUE_NAME, WEEKS_HEADERS, WEEK_DAYS_HEADERS, OCCURRENCES_HEADER, CalendarEvent, WARSAW_TZ


def get_work_week_days_in_month(ref):
    start_of_week = ref - timedelta(days=ref.weekday())

    current_month = ref.month
    days_in_week = [
        (start_of_week + timedelta(days=i)).strftime("%d.%m.%Y")
        for i in range(5)
        if (start_of_week + timedelta(days=i)).month == current_month
    ]

    return days_in_week

def prepare(data):
    schedule = data['schedule']
    timetable = data['timetable']

    if schedule is None or timetable is None:
        return

    dates = get_work_week_days_in_month(datetime.today())

    weeks = {k: v for k, v in schedule.items() if k in WEEKS_HEADERS}

    trans_weeks = {wday: -1 for wday in WEEK_DAYS_HEADERS}

    tkeys = list(trans_weeks.keys())
    for id, date in zip(range(len(dates)), dates):
        for key, values in weeks.items():
            if date in values:
                trans_weeks[tkeys[id]] = WEEKS_HEADERS.index(key) + 1
                break

    result ={}
    for date, (week_day, virtwn) in zip(dates, trans_weeks.items()):
        timetable_day = timetable[week_day]
        for event in timetable_day:
            if virtwn in event[OCCURRENCES_HEADER]:
                if date not in result:
                    result[date] = []
                result[date].append(CalendarEvent.from_dict(event, date=date, timezone=WARSAW_TZ))

    to_send = [v.to_dict() for k, l in result.items() for v in l]
    print(to_send)

    return to_send

if __name__ == "__main__":
    worker = RedisQueueWorker("Data Prepare", redis_url="redis://autocal-redis:6379", queue_name=DATA_QUEUE_NAME)
    worker.listen(prepare)
