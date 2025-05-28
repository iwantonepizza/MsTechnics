import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MsServiceControl.settings")
import django

django.setup()
import redis
from datetime import datetime
import requests
from sorting_message import presend_filters
import time

# Настройка Redis
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
pubsub = redis_client.pubsub()
pubsub.subscribe('ManageControl')

# Время последнего сообщения
last_message_time = datetime.now()

# Флаги для уведомлений
daily_checker_error_state = False  # Уведомление об отключении

# переменные из блока контроля работоспособности сайта
url_to_check = "https://www.mstechnics.ru/sys-check/"
last_status_code = 200

presend_filters(text=f"ManageControl включился", type_msg='manage_control')

try:
    while True:
        try:
            print('Попытка подключения к сайту')
            response = requests.get(url_to_check, timeout=10)
            current_status_code = response.status_code
        except requests.RequestException as e:
            # Если произошла ошибка соединения, устанавливаем код состояния как 0
            current_status_code = 0

        if current_status_code != last_status_code:
            if current_status_code == 200:
                presend_filters(text=f"✅Сайт снова работает! Код состояния: {current_status_code}✅",
                                type_msg='manage_control')
            else:
                presend_filters(text=f"❌Ошибка на сайте ! Код состояния: {current_status_code}❌",
                                type_msg='manage_control')

            # Обновляем последний статус-код
            last_status_code = current_status_code
        else:
            print('Все так же:', last_status_code)

        # Прослушивание сообщений от основного сервиса
        print('Проверка на сообщение чекера')
        message = pubsub.get_message(ignore_subscribe_messages=True)  # Неблокирующий вызов

        if message:
            print('daily_checker still work')
            last_message_time = datetime.now()

            # Если сервер снова активен, отправляем уведомление
            if daily_checker_error_state:
                presend_filters(text="✅Проверка заданий снова активна!✅", type_msg='manage_control')
                daily_checker_error_state = False
        else:
            # Проверяем, прошло ли больше 2 минут с момента последнего сообщения
            print('Проблема:', daily_checker_error_state)
            if (datetime.now() - last_message_time).total_seconds() > 120:
                print('daily_checker не отвечает больше двух минут')
                if not daily_checker_error_state:
                    presend_filters(text="❌Проверка заданий не отвечает!❌", type_msg='manage_control')
                    daily_checker_error_state = True
            print('сплю')
        time.sleep(30)


except Exception as e:
    presend_filters(text=f"Ошибка в Manage Control - {e}", type_msg='manage_control')
