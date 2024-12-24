import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MsServiceControl.settings')
django.setup()

from service.models import *
from user.models import MsUser

allowed_panel_work_status = {'work': {'icon': '🟢', 'ru': 'исправен'},
                             'minor_problems': {'icon': '🟡', 'ru': 'незначительные проблемы'},
                             'problem': {'icon': '🟠', 'ru': 'проблема в работе'},
                             'not_work': {'icon': '🔴', 'ru': 'не работает'},
                             'unrecoverable': {'icon': '⚫', 'ru': 'невосстанавливаемый'}}
links = {'photo_report': 'https://disk.yandex.ru/d/dQUxPqq2ITYqPQ', 'rostelecom_camera': 'https://gclnk.com/hYdCOCx8'}

td_table = {'Ms': 0}

daily_task = {
    'perm': {'photo_report': {'name': 'Фотоотчет', 'repeat': 'daily', 'start_time': time(8, 0, 0),
                              'end_time': time(11, 0, 0),
                              'done_status': None,
                              'link': links['photo_report']},
             'first_9_00': {'name': '1-просмотр 9:00', 'repeat': 'daily', 'start_time': time(9, 0, 0),
                            'end_time': time(13, 0, 0),
                            'done_status': None,
                            'link': links['rostelecom_camera']},
             'second_9_00': {'name': '2-просмотр 9:00', 'repeat': 'daily', 'start_time': time(9, 0, 0),
                             'end_time': time(9, 0, 0),
                             'done_status': None,
                             'link': links['rostelecom_camera']},
             'first_13_00': {'name': '1-просмотр 13:00', 'repeat': 'daily', 'start_time': time(13, 0, 0),
                             'end_time': time(17, 0, 0),
                             'done_status': None,
                             'link': links['rostelecom_camera']},
             'second_13_00': {'name': '2-просмотр 13:00', 'repeat': 'daily', 'start_time': time(13, 0, 0),
                              'end_time': time(17, 0, 0),
                              'done_status': None,
                              'link': links['rostelecom_camera']},
             'first_17_00': {'name': '1-просмотр 17:00', 'repeat': 'daily', 'start_time': time(17, 0, 0),
                             'end_time': time(21, 0, 0),
                             'done_status': None,
                             'link': links['rostelecom_camera']},
             'second_17_00': {'name': '2-просмотр 17:00', 'repeat': 'daily', 'start_time': time(17, 0, 0),
                              'end_time': time(21, 0, 0),
                              'done_status': None,
                              'link': links['rostelecom_camera']},
             'first_21_00': {'name': '1-просмотр 21:00', 'repeat': 'daily', 'start_time': time(21, 0, 0),
                             'end_time': time(23, 0, 0),
                             'done_status': None,
                             'link': links['rostelecom_camera']},
             'second_21_00': {'name': '2-просмотр 21:00', 'repeat': 'daily', 'start_time': time(21, 0, 0),
                              'end_time': time(23, 0, 0),
                              'done_status': None,
                              'link': links['rostelecom_camera']}},

}

daily_task_status = {'not_time': {'icon': '🔒', 'description': 'Ещё не время', 'available': False},
                     'time_start': {'icon': '🔥', 'description': 'Активное задание', 'available': True},
                     'time_burn': {'icon': '👀', 'description': 'Скорее!', 'available': True},
                     'time_end': {'icon': '❌', 'description': 'Задание не выполнено', 'available': False},
                     'done': {'icon': '✅', 'description': 'Выполнено вовремя', 'available': False}}

translated_table = {
    'kolizey': {'ru': {'name': 'Колизей'}, 'short': 'KLZ', 'smile': ''},
    'malkova': {'ru': {'name': 'Малкова'}, 'short': 'MLK'},
    'belinskogo': {'ru': {'name': 'Белинского'}, 'short': 'BLN'}, 'shk': {'ru': {'name': 'ШК'}, 'short': 'SHK'}}

city = {'perm': {'displays': ['kolizey', 'shk', 'belinskogo', 'malkova']}, 'ekat': {'displays': []}}

display_main = {'kolizey': {'params': {'height': 17, 'width': 3}}, 'shk': {'params': {'height': 4, 'width': 15}},
                'belinskogo': {'params': {'height': 9, 'width': 7}}, 'malkova': {'params': {'height': 17, 'width': 13}}}

statuses = {'ru': {'app': '', 'kolizey': 'колизnamей', 'application_sent_to_control': 'создана мониторингом',
                   'application_apply_in_control': 'принят в контроле',
                   'application_sent_to_service': 'отправлен обслуживание',
                   'application_work_in_service': 'принято в работу в сервисе', 'done': 'сервис выполнил ремонт',
                   'application_unable': 'ремонт невозможен', 'archive_done': 'в архиве', 'archive_unable': 'в архиве',
                   'work': 'проблем нет', 'unrecoverable': '❌невосстанавливаемый❌',
                   'minor_problems': 'незначительные проблемы', 'problem': 'проблема в работе',
                   'not_work': 'не работает'}}



statuslcd = {'work': {'color': 'Green', 'description': 'Все отлично', 'icon': 4},
             'minor_problems': {'color': 'Yellow', 'description': 'Небольшие неисправности', 'icon': 6},
             'problem': {'color': 'Orange', 'description': 'Серьезные неполадки', 'icon': 7},
             'error': {'color': 'Red', 'description': 'Критические неполадки', 'icon': 5},
             'unrecoverable': {'color': 'Black', 'description': 'Невосстанавливаемый', 'icon': 8}}


def cr():
    color = {
        "Red": "#FF0000",
        "Green": "#008000",
        "Blue": "#0000FF",
        "Yellow": "#FFFF00",
        "Cyan": "#00FFFF",
        "Magenta": "#FF00FF",
        "Orange": "#FFA500",
        "Purple": "#800080",
        "Pink": "#FFC0CB",
        "Lime": "#00FF00",
        "Teal": "#008080",
        "Indigo": "#4B0082",
        "Violet": "#EE82EE",
        "Gold": "#FFD700",
        "Silver": "#C0C0C0",
        "Brown": "#A52A2A",
        "Olive": "#808000",
        "Maroon": "#800000",
        "Navy": "#000080",
        "Coral": "#FF7F50",
        "Turquoise": "#40E0D0",
        "Salmon": "#FA8072",
        "Khaki": "#F0E68C",
        "Crimson": "#DC143C",
        "Mint": "#98FF98",
        "Lavender": "#E6E6FA",
        "Beige": "#F5F5DC",
        "Periwinkle": "#CCCCFF",
        "Ivory": "#FFFFF0",
        "Peach": "#FFE5B4",
        "Plum": "#DDA0DD",
        "ForestGreen": "#228B22",
        "Chocolate": "#D2691E",
        "SkyBlue": "#87CEEB",
        "Tomato": "#FF6347",
        "SlateGray": "#708090",
        "RoyalBlue": "#4169E1",
        "Orchid": "#DA70D6",
        "DeepPink": "#FF1493",
        "LemonChiffon": "#FFFACD",
        "Black": '#000000',
        "White": '#FFFFFF',
    }
    for name, he in color.items():
        Color.objects.create(name=name, hex_color=he)

    icons = ['❌', '✅', '🔒', '🔥', '🟢', '🔴', '🟡', '🟠', '💀']
    for icon in icons:
        Smile.objects.create(smile_icon=icon)

    for cond, y in statuslcd.items():
        Condition.objects.create(name=cond, color_text=Color.objects.get(name='Black'),
                                 color=Color.objects.get(name=y['color']),
                                 icon=Smile.objects.get(smile_icon=icons[y['icon']]))

    x = {'default': {'color': 'Black', 'description': 'нет заявок', 'icon': 8},
         'application_sent_to_control': {'color': 'Black', 'description': 'создана мониторингом', 'icon': 8},
         'application_apply_in_control': {'color': 'Black', 'description': 'принят в контроле', 'icon': 8},
         'application_sent_to_service': {'color': 'Black', 'description': 'отправлен обслуживание', 'icon': 8},
         'application_work_in_service': {'color': 'Black', 'description': 'принято в работу в сервисе', 'icon': 8},
         'done': {'color': 'Black', 'description': 'сервис выполнил ремонт', 'icon': 8},
         'application_unable': {'color': 'Black', 'description': 'ремонт невозможен', 'icon': 8}, 'archive_done': {
            'color': 'Black', 'description': 'в архиве', 'icon': 8},
         'archive_unable': {'color': 'Black', 'description': 'в архиве', 'icon': 8}
         }
    for n, d in x.items():
        ApplicationStatus.objects.create(name=n, color_text=Color.objects.get(name='Black'),
                                         description=d['description'], color=Color.objects.get(name=d['color']),
                                         icon=Smile.objects.get(smile_icon=icons[d['icon']]))

    # x = {'work': {'color': 'green', 'icon': 4, 'description': 'исправен'},
    #      'minor_problems': {'color': 'yellow', 'icon': 6, 'description': 'незначительные проблемы'},
    #      'problem': {'color': 'orange', 'icon': 7, 'description': 'проблема в работе'},
    #      'not_work': {'color': 'red', 'icon': 5, 'description': 'не работает'},
    #      'unrecoverable': {'color': 'black', 'icon': 8, 'description': 'невосстанавливаемый'}}
    #
    # for name, y in x.items():
    #     PanelStatus.objects.create(name=name, description=y['description'], color=Color.objects.get(name=y['color'])
    #                                , icon=Smile.objects.get(smile_icon=icons[y['icon']]))

    for c, x in city.items():
        xxx = Cities.objects.create(name=c)
        for d in x['displays']:
            Display.objects.create(name=d, description='ТЕСТ',
                                   rows=display_main[d]['params']['height'], cols=display_main[d]['params']['width'],
                                   condition=Condition.objects.get(name='work'),
                                   city=xxx)

    x = {'zip': {'color': 'Green', 'icon': 4, 'description': 'зип'},
         'service': {'color': 'Yellow', 'icon': 6, 'description': 'в сервисе'},
         'hand': {'color': 'Orange', 'icon': 7, 'description': 'на руках'},
         'monitor': {'color': 'Red', 'icon': 5, 'description': 'на экране'},
         'unknown': {'color': 'Black', 'icon': 8, 'description': 'неизвестно'}}
    for name, y in x.items():
        Department.objects.create(name=name, color_text=Color.objects.get(name='Black'), description=y['description'],
                                  color=Color.objects.get(name=y['color'])
                                  , icon=Smile.objects.get(smile_icon=icons[y['icon']]))

    for i in range(1, 300):
        condition = Condition.objects.all()
        department = Department.objects.all()
        display = Display.objects.all()
        app_statue = ApplicationStatus.objects.get(name='default')
        Panels.objects.create(name=f'KLZ-{i}', display=display.get(name='kolizey'),
                              condition=condition.get(name='work'),
                              department=department.get(name='zip'),
                              application_status=app_statue)
        Panels.objects.create(name=f'SHK-{i}', display=display.get(name='shk'),
                              condition=condition.get(name='work'),
                              department=department.get(name='zip'),
                              application_status=app_statue)
        Panels.objects.create(name=f'BLN-{i}', display=display.get(name='belinskogo'),
                              condition=condition.get(name='work'),
                              department=department.get(name='zip'),
                              application_status=app_statue)
        Panels.objects.create(name=f'MLK-{i}', display=display.get(name='malkova'),
                              condition=condition.get(name='work'),
                              department=department.get(name='zip'),
                              application_status=app_statue)

    if not MsUser.objects.exists():
        MsUser.objects.create(username='root', is_superuser=True, password=2, is_staff=True, is_active=True,
                              permission='technical', first_name='Petro', last_name='Poroshenko', )

    for cityz, tasks in daily_task.items():
        for name, task in tasks.items():
            DailyTask.objects.create(name=task['name'], description='описание', city=Cities.objects.get(name=cityz),
                                     status='undone', start_time=task['start_time'], end_time=task['end_time'],
                                     link=task['link'])

    for display in Display.objects.all():
        all_cells = [(row, col) for row in range(1, display.rows + 1) for col in range(1, display.cols + 1)]
        for row, col in all_cells:
            Cell.objects.create(display=display, row=row, col=col)

#cr()
