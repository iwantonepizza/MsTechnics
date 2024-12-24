from datetime import datetime

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from MsServiceControl.settings import ALLOWED_DEPARTMENT
from core_mechanic.Data.Db.orm_query import get_panel_history_report
from zip.models import Panels
from core_mechanic.get_time import get_time_setting_tz
from departure.models import Departure
from application.utils import get_filter_application
from main_menu.models import PanelHistoryReport


@login_required
def index(request):
    user = request.user
    chosen_panel = request.GET.get('chosen_panel', None)
    mode = request.GET.get('mode', None)
    comment = request.GET.get('comment', None)
    description = request.GET.get('description', None)
    user = request.user
    current_datetime = request.GET.get('time', None)
    if not current_datetime:
        current_datetime = get_time_setting_tz()
    else:
        current_datetime = datetime.fromisoformat(current_datetime)
    if mode == 'add_service_comment':
        if chosen_panel:
            if comment:
                PanelHistoryReport.objects.create(panel=Panels.objects.get(name=chosen_panel),
                                                  description=comment,
                                                  type_report='service', comment=f'добавлен вручную',
                                                  time=current_datetime, user=f'{user.first_name} {user.last_name}')

    applications = get_filter_application()
    move_report = get_panel_history_report(type_report='moving')
    departures = Departure.objects.all().order_by('-time_created')
    panel_service_report = get_panel_history_report().filter(type_report='service')
    panels = Panels.objects.all()

    context = {'title': 'Общее меню',
               'allowed': ALLOWED_DEPARTMENT,
               'panel_service_report': panel_service_report,
               'applications': applications,
               'move_report': move_report,
               'departures': departures,
               'panels': panels}
    return render(request, 'main_menu/menu.html', context)
