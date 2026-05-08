from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

from application.models import ApplicationHistoryReport
from zip.models import Display, Panels
from main.Db.orm_query import get_today_daily, done_daily
from application.utils import get_display_application

from main.models import Cities
from django.db.models import Count


@login_required
def index_monitoring(request):
    all_city = Cities.objects.annotate(display_count=Count('display')).filter(
        display_count__gt=0)  # Только города с экранами

    context = {'title': 'Меню мониторинг',
               'all_city': all_city,
               'department': 'monitoring'}
    return render(request, f'main_menu/main_department_menu.html', context)


@login_required
def monitoring_main(request, city_name, display_name):
    panel_id = request.GET.get('panel_id', None)
    application_box_chosen = request.GET.get('application_box_chosen', 'quest')
    task = request.GET.get('task')
    url = request.GET.get('url')

    user_cities = request.user.allowed_city.all()  # Получаем Queryset всех городов
    user_access = any(city.name == city_name for city in user_cities)

    user = request.user

    application_report = ApplicationHistoryReport.objects.order_by('-time')

    display = (
        Display.objects
        .prefetch_related(
            "cell_set__panel__application_status",  # Цвета заявок
            "cell_set__panel__condition",  # Состояние панели
            "cell_set__panel__condition__icon",
            "cell_set__panel__department",
            "cell_set__panel__display"
        )
        .get(name=display_name)
    )

    if panel_id and panel_id != 'ПУСТО':
        panel = Panels.objects.select_related('condition__icon').get(name=panel_id)
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
        'application_box_chosen': application_box_chosen,
        'applications': applications_at_display,
        'daily': tasks,
        'display': display,
        'user_access': user_access,
        'application_report': application_report,

        # для верхнего навбара
        'department': 'monitoring'

    }
    return render(request, f'monitoring/monitoring_base.html', context)
