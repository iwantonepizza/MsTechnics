from django.contrib.auth.decorators import login_required

from project_config.settings import ALLOWED_DEPARTMENT
from departure.models import Departure, Executor
from main_menu.models import PanelHistoryReport
from application.models import Application
import json

from django.shortcuts import render
from django.http import JsonResponse

from zip.models import Panels


@login_required
def index(request):
    user = request.user

    applications = Application.objects.select_related(
        'panel',
        'display',
        'cell',
        'status',
        'executor'
    ).all().order_by('-last_update_date_time')

    service_applications = applications.filter(status__name='sent_to_service')

    departures = []

    executors = Executor.objects.all()

    panel_reports = PanelHistoryReport.objects.select_related("panel").all().order_by('-time')
    panel_service_report = panel_reports.filter(type_report='service')

    context = {'title': 'Общее меню',
               'allowed': ALLOWED_DEPARTMENT,
               'panel_service_report': panel_service_report,
               'applications': applications,
               'service_applications': service_applications,
               'panel_reports': panel_reports,
               'departures': departures,
               'executors': executors}
    return render(request, 'main_menu/menu.html', context)


@login_required()
def get_application_color_info(request):
    return render(request, "modals/application_color_info.html")


@login_required()
def panel_condition_confirm(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Загружаем JSON
            return render(request, "modals/panel_condition_confirm.html", data)  # 🔹 Передаем ВСЕ параметры в шаблон
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required()
def create_application_confirm(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Загружаем JSON
            panel = Panels.objects.get(id=data['panel_id'])

            return render(request, "modals/create_application.html", {'panel': panel})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)
