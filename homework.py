"""Телеграмм Бот.

Проверяет статус проверки финальной работы в ЯПрактикуме ревьювером.
"""
import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler
from logging.handlers import RotatingFileHandler
from typing import Any, Optional

import requests
from dotenv import load_dotenv
from telebot import TeleBot

from exceptions import StatusNotOk


load_dotenv()

PRACTICUM_TOKEN: Optional[str] = os.getenv('VERIFICATION_CODE')
TELEGRAM_TOKEN: Optional[str] = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID: Optional[str] = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD: int = 600
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: dict[str, str] = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

ALL_WORKS: bool = False  # True - для запроса всех работ.
DAYS_AGO: int = 21
SECOND_IN_DAY: int = 86400  # Секунд в сутках.

HOMEWORK_VERDICTS: dict[str, str] = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

KEY_HOMEWORKS: str = 'homeworks'
KEY_FROM_DATE: str = 'from_date'
KEY_STATUS: str = 'status'
KEY_LESSON_NAME: str = 'homework_name'  # 'lesson_name' было бы лучше.
INDEX_LAST_HOMEWORKS: int = 0


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler_file = RotatingFileHandler(
    'logger.log',
    maxBytes=50000000,
    backupCount=5,
    encoding='utf-8'
)
handler_stream = StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler_file.setFormatter(formatter)
handler_stream.setFormatter(formatter)
logger.addHandler(handler_file)
logger.addHandler(handler_stream)


def check_tokens() -> None:
    """Проверка на наличие токенов."""
    check_list: list = [PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN]
    check: bool = all(check_list)
    if not check:
        message_err: str = 'Отсутствует доступ к необходимым токенам и/или ID!'
        logger.critical(f'{message_err}')
        exit(1)


def send_message(bot: TeleBot, message: str) -> None:
    """Функция отправляет сообщение."""
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )
    logger.debug('Сообщение отправлено.')


def get_api_answer(timestamp: int) -> dict[str, Any]:
    """Функция отправляет запрос.

    Принимает временной промежуток в секундах, возвращает словарь.
    """
    payload: dict[str, int] = {KEY_FROM_DATE: timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
        if response.status_code != HTTPStatus.OK:
            massage_error: str = ('Запрос к основному API вернул код не 200, а'
                                  f'{ response.status_code}.')
            logger.error(massage_error)
            raise StatusNotOk(massage_error)
        response.raise_for_status()
    except requests.exceptions.RequestException as error:
        logger.error(f'Ошибка при запросе к основному API. {error}')
    api_answer: dict[str, Any] = response.json()
    return api_answer


def check_response(response: dict[str, Any]):
    """Функция проверяет ответ на запрос.

    Принимает ответ на запрос в виде словаря, возвращает словарь с данными по
    последней работе.
    """
    try:
        homework: list = response[KEY_HOMEWORKS]
    except KeyError:
        logger.error(
            f'В ответе от API нет ключа {KEY_HOMEWORKS}.'
        )
        raise KeyError('{KEY_HOMEWORKS} отсутствует в ответе основного API.')
    if type(response[KEY_HOMEWORKS]) is not list:
        message_error_key: str = (
            f'Под ключём {KEY_HOMEWORKS} хранится не список.'
        )
        logger.error(message_error_key)
        raise TypeError(message_error_key)
    try:
        last_homeworks: dict[str, Any] = homework[INDEX_LAST_HOMEWORKS]
    except IndexError:
        message_error_index: str = (
            f'Список работ полученный по ключу {KEY_HOMEWORKS} оказался пуст.'
        )
        logger.debug(message_error_index)
        raise IndexError(message_error_index)
    else:
        return last_homeworks


def parse_status(homework: dict[str, Any]) -> str:
    """Функция проверяет статуса работы и подгатавлевает сообщение."""
    try:
        status: str = homework[KEY_STATUS]
        homework_name: str = homework[KEY_LESSON_NAME]
    except KeyError:
        message_error_key: str = (
            'В словаре с данными об отдельной работе не обнаружен один из '
            f'ключей {KEY_STATUS}, {KEY_LESSON_NAME}.'
        )
        logger.error(message_error_key)
        raise KeyError(message_error_key)
    try:
        verdict = HOMEWORK_VERDICTS[status]
    except KeyError:
        message_error_key_: str = (
            f'Неожиданное значение стауса работы: {status}.'
        )
        logger.error(message_error_key_)
        raise KeyError(message_error_key_)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> None:
    """Основная логика работы бота."""
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    from_date: int = 0
    if not ALL_WORKS:
        from_date = timestamp - DAYS_AGO * SECOND_IN_DAY
    message_old_status: str = ''
    message_old_error: str = ''

    while True:
        try:
            check_tokens()
            api_answer = get_api_answer(from_date)
            last_homeworks = check_response(api_answer)
            message_now_status = parse_status(last_homeworks)
            if message_now_status != message_old_status:
                send_message(bot, message_now_status)
                message_old_status = message_now_status
            else:
                logger.debug('Отсутствует новые статусы.')
        except Exception as error:
            message_now_error = f'Сбой в работе программы: {error}'
            logger.error(message_now_error)
            if message_now_error != message_old_error:
                try:
                    send_message(bot, message_now_error)
                    message_old_error = message_now_error
                except Exception:
                    pass

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
