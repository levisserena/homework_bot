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
import simplejson
from dotenv import load_dotenv
from telebot import TeleBot
from telegram.error import TelegramError

from exceptions import StatusNotOk
from utilities import datatime_unix


load_dotenv()

PRACTICUM_TOKEN: Optional[str] = os.getenv('VERIFICATION_CODE')
TELEGRAM_TOKEN: Optional[str] = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID: Optional[str] = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD: int = 600
UTC: int = 14400  # +4 часа для Астрахани в секундах.
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
KEY_CURRENT_DATE: str = 'current_date'
KEY_FROM_DATE: str = 'from_date'
KEY_STATUS: str = 'status'
KEY_LESSON_NAME: str = 'homework_name'  # 'lesson_name' было бы лучше.
KEY_DATE_UPDATED: str = 'date_updated'
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
        logger.critical('Отсутствует доступ к необходимым токенам и/или ID!')
        exit(1)


def send_message(bot: TeleBot, message: str) -> None:
    """Функция отправляет сообщение."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.debug('Сообщение отправлено.')
    except TelegramError:
        message_error: str = 'Сообщение не отправлено.'
        logger.error(message_error)
        raise TelegramError('Сообщение не было доставлено.')


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
            raise StatusNotOk('Запрос к основному API вернул код не "200", а'
                              f'"{response.status_code}".')
        response.raise_for_status()
    except requests.exceptions.RequestException as error:
        raise error(f'Ошибка при запросе к основному API. {error}')
    try:
        api_answer: dict[str, Any] = response.json()
    except simplejson.errors.JSONDecodeError as error:
        raise error('При попытке JSON преобразовать в пригородные для Python '
                    'формат произошла ошибка.')
    return api_answer


def check_response(response: dict[str, Any]) -> dict[str, Any]:
    """Функция проверяет ответ на запрос.

    Принимает ответ на запрос в виде словаря, возвращает словарь с данными по
    последней работе, а также дату последнего запороса в формате Unix.
    """
    try:
        current_date: int = response[KEY_CURRENT_DATE]
    except KeyError:
        raise KeyError(f'В ответе от API нет ключа "{KEY_CURRENT_DATE}".')

    if type(current_date) is not int:
        raise TypeError(f'Под ключом "{KEY_CURRENT_DATE}" хранится не целое '
                        'число.')

    try:
        homework: list = response[KEY_HOMEWORKS]
    except KeyError:
        raise KeyError(f'В ответе от API нет ключа "{KEY_HOMEWORKS}".')

    if type(homework) is not list:
        raise TypeError(f'Под ключом "{KEY_HOMEWORKS}" хранится не список.')

    try:
        last_homeworks: dict[str, Any] = homework[INDEX_LAST_HOMEWORKS]
    except IndexError:
        raise IndexError(f'Список работ полученный по ключу {KEY_HOMEWORKS} '
                         'оказался пуст.')

    return last_homeworks


def parse_status(homework: dict[str, Any]) -> str:
    """Функция проверяет статуса работы и подготавливает сообщение."""
    try:
        status: str = homework[KEY_STATUS]
        homework_name: str = homework[KEY_LESSON_NAME]
    except KeyError:
        raise KeyError('В словаре с данными об отдельной работе не обнаружен '
                       f'один из ключей "{KEY_STATUS}", "{KEY_LESSON_NAME}".')

    try:
        verdict = HOMEWORK_VERDICTS[status]
    except KeyError:
        raise KeyError(f'Неожиданное значение статуса работы: {status}.')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def parse_date_updated(homework: dict[str, Any]) -> str:
    """Функция возвращает дату изменения статуса в виде строки."""
    try:
        date_updated: str = homework[KEY_DATE_UPDATED]
    except KeyError:
        raise KeyError('В словаре с данными об отдельной работе не обнаружен '
                       f'ключ "{KEY_DATE_UPDATED}".')
    return date_updated


def main() -> None:
    """Основная логика работы бота."""
    bot = TeleBot(token=TELEGRAM_TOKEN)

    from_date: int = 0
    old_from_date: int = 0
    message_old_error: str = ''

    check_tokens()

    while True:
        try:
            if not old_from_date:
                from_date = old_from_date
            api_answer = get_api_answer(from_date)
            last_homeworks = check_response(api_answer)
            message_status = parse_status(last_homeworks)
            date_time_str = parse_date_updated(last_homeworks)
            new_from_date = datatime_unix(date_time_str) + UTC
            if old_from_date != new_from_date:
                send_message(bot, message_status)
                old_from_date = new_from_date
            else:
                logger.debug('Отсутствует новые статусы.')
        except Exception as error:
            message_now_error = f'Сбой в работе программы: {error}'
            logger.error(message_now_error)
            if message_now_error != message_old_error:
                try:
                    send_message(bot, message_now_error)
                    message_old_error = message_now_error
                except Exception as error:
                    logger.error('Сообщение об ошибке в Телеграм не доставлено'
                                 f'{error}')

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
