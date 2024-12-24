import os
import datetime
import redis
from core_mechanic.get_time import get_time_setting_tz

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MsServiceControl.settings")

import django

django.setup()

from zip.models import DailyTask
from core_mechanic.telegram_connect import send_tg_notification
from time import sleep


def result_analyse(pre_result) -> dict:
    end_result = {}
    for task_name, pre_result_in in pre_result.items():
        end_result[task_name] = {}
        if pre_result_in:
            for user_name, msg_status in pre_result_in.items():
                if msg_status == 200:
                    end_result[task_name].update({user_name: '🟢'})
                else:
                    end_result[task_name].update({user_name: '🔴'})
    return end_result


redis_client = redis.StrictRedis(host='localhost', port=6380, db=0)
try:
    send_tg_notification(text=f'Перезагрузка чекера',
                         type_msg='server_checker'
                         )
    while True:
        current_datetime = get_time_setting_tz()
        iteration_result = {}

        for task in DailyTask.objects.all():
            iteration_done = task.check_iteration(current_datetime)
            if iteration_done:
                iteration_result[task.name] = {}
                for user, code in iteration_done.items():
                    iteration_result[task.name][user.username] = code

        if current_datetime.time() > datetime.time(23, 58, 59):
            for task in DailyTask.objects.all():
                task.reset_task()
            send_tg_notification(text=f'🍕',
                                 type_msg='server_checker'
                                 )

        if iteration_result:
            result = result_analyse(iteration_result)

            text_result = ''
            for task, new_result in result.items():
                text_result += f'\n---------------\n{task}:'
                if new_result:
                    for user, status in new_result.items():
                        text_result += f'\n{status} - {user}'
                else:
                    text_result += f'⚪️'
            send_tg_notification(text=f'{text_result}',
                                 type_msg='server_checker'
                                 )
        redis_client.publish('server_checker', '⚪️') # пустота
        iteration_result.clear()
        sleep(60)
except Exception as e:
    send_tg_notification(text=f'Ошибка чекера - {e}',
                         type_msg='server_checker'
                         )
    redis_client.publish('server_checker', f'Ошибка чекера - {e}')

