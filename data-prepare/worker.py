from datetime import datetime, timedelta
from shared import RedisQueueWorker

DATA_QUEUE_NAME = "data_queue"
GOOGLE_API_QUEUE_NAME = "google_api_queue"

def get_work_week_days_in_month(ref):
    ref
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

    weeks = {k: v for k, v in schedule.items() if k != "year"}

    wheaders = ("t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10", "t11", "t12", "t13", "t14", "t15")

    trans_weeks = {"Monday": -1, "Tuesday": -1, "Wednesday": -1, "Thursday": -1, "Friday": -1}

    tkeys = list(trans_weeks.keys())
    for id, date in zip(range(5), dates):
        for key, values in weeks.items():
            if date in values:
                trans_weeks[tkeys[id]] = wheaders.index(key) + 1
                break

    print(trans_weeks)

    result ={}
    for date, (week_day, virtwn) in zip(dates, trans_weeks.items()):
        timetable_day = timetable[week_day]
        for event in timetable_day:
            if virtwn in event["occurrences"]:
                if date not in result:
                    result[date] = []
                result[date].append(event)

    print(result)

if __name__ == "__main__":
    worker = RedisQueueWorker("Data Prepare", redis_url="redis://autocal-redis:6379", queue_name=DATA_QUEUE_NAME)
    worker.listen(prepare)

    # today = datetime.today()
    # print(get_week_days_in_month(today))
