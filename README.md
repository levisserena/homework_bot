# Homework telegram bot
### О проекте.
Телеграм бот.
Отсылает сообщение указанному клиенту Телеграм,
о изменение статуса проверки работы ревьювером, с API сервиса
ЯндексПрактикум.
___
### Информация об авторах.
Акчурин Лев Ливатович.<br>
[Страничка GitHub](https://github.com/levisserena)
___
### При создании проекта использовалось:
- язык программирования [Python 3](https://www.python.org/);
- библиотека [pyTelegramBotAPI](https://pypi.org/project/pyTelegramBotAPI/);
- библиотека [python-telegram-bot](https://pypi.org/project/python-telegram-bot/).
___
### Реализовано:
- API запросы к удаленному серверу.
- Отсылка сообщения об изменение статуса работы.
___
### Чтобы развернуть проект необходимо следующие:
- Клонировать репозиторий со своего GitHub и перейти в него в командной строке:

```
git clone git@github.com:levisserena/homework_bot.git
```
>*Активная ссылка на репозиторий под этой кнопкой* -> [КНОПКА](https://github.com/levisserena/homework_bot)
- Перейдите в папку с проектом:
```
cd homework_bot
```
- Создать и активировать виртуальное окружение:

Windows
```
python -m venv venv
source venv/Scripts/activate
```
Linux
```
python3 -m venv venv
source3 venv/bin/activate
```
- Установить зависимости:
```
python -m pip install --upgrade pip
pip install -r requirements.txt
```
- Заполнить `.env` согласно `.env.example`.
```
```
- Запустите bot:

```
python homework.py
```
___
<p align="center">
<img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54">
<img src="https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white">
</p>
