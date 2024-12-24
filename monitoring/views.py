from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

from MsServiceControl.settings import ALLOWED_DEPARTMENT
from zip.models import Display
from core_mechanic.Data.Db.orm_query import get_today_daily, done_daily, get_filter_panels
from application.utils import get_display_application

from main.models import Cities


@login_required
def index_monitoring(request):
    all_city = Cities.objects.all()
    context = {'title': 'Меню мониторинг',
               'all_city': all_city,

               'allowed': ALLOWED_DEPARTMENT,
               'department': 'monitoring'}
    return render(request, f'main_menu/main_department_menu.html', context)


@login_required
def monitoring_main(request, city_name, display_name):
    panel_id = request.GET.get('panel_id', None)
    left_bar_status = request.GET.get('left_bar_status', 'quest')
    task = request.GET.get('task')
    url = request.GET.get('url')

    user = request.user

    display = Display.objects.get(name=display_name)

    if panel_id and panel_id != 'ПУСТО':
        panel = get_filter_panels(panel_id).first()
    else:
        panel = None

    tasks = get_today_daily(city_name)
    if url and task:
        done_daily(int(task), user=user, result='выполнено в срок')
        return redirect(url)

    applications_at_display = get_display_application(display_name=display_name)

    context = {
        'title': f'Мониторинг {display.description}',
        'panel': panel,
        'left_bar_status': left_bar_status,
        'applications': applications_at_display,
        'daily': tasks,
        'display': display,

        # для верхнего навбара
        'allowed': ALLOWED_DEPARTMENT,
        'department': 'monitoring'

    }
    return render(request, f'monitoring/monitoring_base.html', context)
