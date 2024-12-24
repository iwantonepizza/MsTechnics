import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MsServiceControl.settings")
import django

django.setup()
import redis
from datetime import datetime, timedelta
import requests
from core_mechanic.telegram_connect import send_tg_notification
import time

# Настройка Redis
redis_client = redis.StrictRedis(host='localhost', port=6380, db=0)
pubsub = redis_client.pubsub()
pubsub.subscribe('server_checker')

# Время последнего сообщения
last_message_time = datetime.now()

# Флаги для уведомлений
daily_all_ok = False  # Уведомление об отключении

# переменные из блока контроля работоспособности сайта
url_to_check = "https://www.mstechnics.ru/sys-check/"
last_status_code = 200

try:
    while True:
        try:
            # Попытка подключения к сайту
            response = requests.get(url_to_check, timeout=10)
            current_status_code = response.status_code
        except requests.RequestException as e:
            # Если произошла ошибка соединения, устанавливаем код состояния как 0
            current_status_code = 0

            # Если статус-код изменился
        if current_status_code != last_status_code:
            if current_status_code == 200:
                # Уведомление, если сайт снова работает
                send_tg_notification(text=f"✅Сайт снова работает! Код состояния: {current_status_code}✅",
                                     type_msg='status_checker')
            else:
                # Уведомление об ошибке
                send_tg_notification(text=f"❌Ошибка на сайте ! Код состояния: {current_status_code}❌",
                                     type_msg='status_checker')

            # Обновляем последний статус-код
            last_status_code = current_status_code

        # Прослушивание сообщений от основного сервиса
        # message = pubsub.get_message()

        message = pubsub.get_message(ignore_subscribe_messages=True)  # Неблокирующий вызов
        if message:
            last_message_time = datetime.now()

            # Если сервер снова активен, отправляем уведомление
            if daily_all_ok:
                send_tg_notification(text="✅Проверка заданий снова активна!✅", type_msg='server_checker')
                daily_all_ok = False  # Сброс флага

        # Проверяем, прошло ли больше 2 минут с момента последнего сообщения
        if (datetime.now() - last_message_time).total_seconds() > 120:
            if not daily_all_ok:
                send_tg_notification(text="❌Проверка заданий не отвечает!❌", type_msg='server_checker')
                daily_all_ok = True  # Устанавливаем флаг, чтобы не спамить
        time.sleep(30)


except Exception as e:
    send_tg_notification(text=f"Ошибка в контрольном сервисе - {e}", type_msg='server_checker')
