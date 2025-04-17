import json
import importlib.resources as pkg_resources
from datetime import datetime
import re

from jsonschema import validate, ValidationError

class BadJsonFormatException(Exception):
    def __init__(self, message="Invalid JSON format"):
        super().__init__(message)

def load_schema(filename: str):
    with pkg_resources.files(__package__).joinpath(filename).open('r', encoding='utf-8') as f:
        return json.load(f)

def validate_json(content: bytes, schema: dict) -> dict:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise BadJsonFormatException(f"Invalid JSON syntax: {e}")

    try:
        validate(instance=data, schema=schema)
    except ValidationError as e:
        raise BadJsonFormatException(
            f"Schema validation error: {e.message}")

    return data


class JsonValidator:
    def __init__(self):
        try:
            with pkg_resources.files(__package__).joinpath("t-schema.json").open("r", encoding="utf-8") as tf, \
                 pkg_resources.files(__package__).joinpath("s-schema.json").open("r", encoding="utf-8") as sf:
                try:
                    self.schedule_sch = json.load(sf)
                    self.timetable_sch = json.load(tf)
                except json.JSONDecodeError as e:
                    raise BadJsonFormatException(
                        f"Invalid JSON shema syntax: {e}")
        except OSError as e:
            raise BadJsonFormatException(f"File not exists: {e}")

    def __check_times(self, entry) -> bool:
        start_str = entry["time"]["start"]
        end_str = entry["time"]["end"]
        start_time = datetime.strptime(start_str, "%H:%M")
        end_time = datetime.strptime(end_str, "%H:%M")

        return start_time >= end_time

    def __check_occurrences(self, entry) -> bool:
        value = entry["occurrences"]
        if value in ['parz', 'nparz']:
            return False

        pattern = r"^\d+(-\d+)?$"
        if not all(bool(re.fullmatch(pattern, s)) for s in value.split(",")):
            return True

        return False

    def validate_timetable(self, content: bytes) -> dict:
        data = validate_json(content, self.timetable_sch)

        for day, entries in data.items():
            for entry in entries:
                try:
                    if self.__check_times(entry):
                        raise BadJsonFormatException(
                            f"In '{day}', event '{entry.get('title', '')}' has start time >= end time"
                        )
                    if self.__check_occurrences(entry):
                        raise BadJsonFormatException(
                            f"In '{day}', event '{entry.get('title', '')}' has unsupported occurrences type"
                        )
                except (ValueError, KeyError) as e:
                    raise BadJsonFormatException(
                        f"Invalid time format or structure in '{day}': {e}")

        return data

    def validate_schedule(self, content: bytes) -> dict:
        data = validate_json(content, self.schedule_sch)

        year = data["year"]
        weeks = {k: v for k, v in data.items() if k != "year"}

        for week in weeks:
            for date_str in data[week]:
                try:
                    day, month = map(int, date_str.split('.'))
                    datetime(year=year, month=month, day=day)
                except (ValueError, TypeError) as e:
                    raise BadJsonFormatException(
                        f"Invalid date '{date_str}' in field '{week}'. Must be a valid calendar date in {year} (format DD.MM)"
                    )

        return data

    def parse_schedule(self, content: bytes) -> dict:
        data = self.validate_schedule(content)

        return data

    def __parse_occurrences(self, otype: str) -> list:
        res = []
        if otype == "parz":
            res = [i for i in range(2, 15, 2)]
        elif otype == "nparz":
            res = [i for i in range(1, 16, 2)]
        else:
            values = otype.split(",")
            for val in values:
                rng = val.split("-")
                if len(rng) == 2:
                    res += [i for i in range(int(rng[0]), int(rng[1]) + 1)]
                else:
                    res.append(int(rng[0]))

        return res

    def parse_timetable(self, content: bytes) -> dict:
        data = self.validate_timetable(content)

        for day, entries in data.items():
            for entry in entries:
                occurrences = entry["occurrences"]

                entry["occurrences"] = self.__parse_occurrences(occurrences)

        return data