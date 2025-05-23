from google.auth import default
import requests
import click
import pickle

from google_auth_oauthlib.flow import InstalledAppFlow


def api_call(func):
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        if res is None:
            print("❌ Błąd")
        elif res.status_code == 200:
            print("✅ Sukces!")
        else:
            print(f"❌ Błąd: {res.json().get('detail')}")
        return res

    return wrapper


@api_call
def config_cmd():
    schedule_path = "data/schedule.json"
    timetable_path = "data/timetable.json"
    token_path = "token.json"

    with (
        open(schedule_path, "r") as sf,
        open(timetable_path, "r") as tf,
        open(token_path, "r") as tkf,
    ):
        files = {
            "token": ("token.json", tkf, "application/json"),
            "schedule": ("schedule.json", sf, "application/json"),
            "timetable": ("timetable.json", tf, "application/json"),
        }

        res = requests.post("http://0.0.0.0:8000/config", files=files, timeout=10)

        if res.status_code == 200:
            response_data = res.json()

            if "config_id" in response_data:
                config_id = response_data["config_id"]
                with open("config_id.pkl", "wb") as f:
                    pickle.dump(config_id, f)
                print(f"💾 Zapisano config_id: {config_id}")
            else:
                print("⚠️ Brak pola '_id' w odpowiedzi")

        return res


@click.group()
def cli():
    pass


@cli.command()
def config():
    config_cmd()


@cli.command()
def register():
    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    credentials_path = "credentials.json"

    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
    creds = flow.run_local_server(port=2255)

    with open("token.json", "w") as token:
        token.write(creds.to_json())


@api_call
@cli.command()
@click.option(
    "-o",
    "--offset",
    default=0,
    type=int,
    help="Offset tygodnia (-1: zeszły, 0: aktualny, 1: przyszły)",
)
def export(offset):
    try:
        with open("config_id.pkl", "rb") as f:
            config_id = pickle.load(f)
        print(f"📖 Użyto config_id z pliku: {config_id}")
    except FileNotFoundError:
        print("⚠️ Brak pliku config_id.pkl")
        return None

    # Wyjaśnienie offsetu dla użytkownika
    offset_desc = {-1: "zeszły tydzień", 0: "aktualny tydzień", 1: "przyszły tydzień"}
    week_desc = offset_desc.get(offset, f"tydzień z offsetem {offset}")
    print(f"📅 Generowanie planu dla: {week_desc}")

    url = "http://0.0.0.0:8000/export"
    data = {"config_id": config_id, "offset": offset}
    headers = {"Content-Type": "application/json"}

    res = requests.post(url, json=data, headers=headers)

    if res.status_code == 200:
        print(f"odpowiedź: {res.json()}")

    return res


def endpoint_action(func):
    res = func()

    if res.status_code == 200:
        print("✅ Sukces!")
        print(f"odpowiedź: {res.json()}")
    else:
        print(f"❌ Błąd: {res.json().get('detail')}")

    print(res)


if __name__ == "__main__":
    # register()
    # endpoint_action(export)
    cli()
