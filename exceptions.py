"""Исключения."""


class StatusNotOk(Exception):
    """Исключение - статус ответа от API не 200."""

    pass


class RequestException(Exception):
    """Исключение - Ошибка при запросе к основному API."""

    pass
