"""Полезные функции."""
from datetime import datetime
from time import mktime

format: str = '%Y-%m-%dT%H:%M:%SZ'


def datatime_unix(date_time_str: str) -> int:
    """Преобразует дату в формат Unix."""
    try:
        date_time_obj = datetime.strptime(date_time_str, format)
    except ValueError:
        raise ValueError('Формат даты передан не верный.')
    result: int = int(mktime(date_time_obj.timetuple()))
    return result
