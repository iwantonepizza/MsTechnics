import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MsServiceControl.settings')
django.setup()

import datetime
import redis
from get_time import get_time_setting_tz

from zip.models import DailyTask
from sorting_message import presend_filters
from time import sleep

"""Сервис по проверке и обновлению ежедневных заданий"""

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

try:
    presend_filters(text=f'Сервис по проверке ежедневных заданий перезагрузился',
                    type_msg='manage_control'
                    )
    while True:
        current_datetime = get_time_setting_tz()
        print('Иттерация дейличкера')

        for task in DailyTask.objects.all():
            task.check_iteration(current_datetime)

        if current_datetime.time() > datetime.time(23, 58, 59):
            for task in DailyTask.objects.all():
                task.reset_task()
            presend_filters(text=f'🍕',
                            type_msg='manage_control'
                            )

        redis_client.publish('ManageControl', '1')  # пустота
        sleep(60)
except Exception as e:
    presend_filters(text=f'Ошибка чекера - {e}',
                    type_msg='manage_control'
                    )
    redis_client.publish('ManageControl', f'Ошибка в чекере - {e}')
