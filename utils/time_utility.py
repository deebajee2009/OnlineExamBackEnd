import datetime
from typing import Final


DATETIME_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT: Final[str] = "%Y-%m-%d"


def convert_str_into_datetime(_datetime: str) -> datetime.datetime:
    return datetime.datetime.strptime(_datetime, DATETIME_FORMAT)


def convert_datetime_into_str(_datetime: datetime.datetime) -> str:
    return datetime.datetime.strftime(_datetime, DATETIME_FORMAT)
