from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from main_menu.models import PanelHistoryReport
from zip.models import Display, Panels, Cell, Lamels, Wires, Hubs
from core_mechanic.Data.Db.orm_query import get_filter_panels, q_panels_change_department, \
    get_formated_panel_history_report
from application.models import ApplicationStatus
from core_mechanic.get_time import get_time_setting_tz
from datetime import datetime
from main.models import Condition, Department


@login_required
def index(request, id_panel=None):
    panel_id = request.GET.get('id', None)
    display_name = request.GET.get('display_name', None)
    input_id = request.GET.get('input_id', None)
    input_model = request.GET.get('input_model', None)
    comment = request.GET.get('comment', 'Комментария нет')
    panels = get_filter_panels
    user = request.user
    current_datetime = request.GET.get('time', None)
    if not current_datetime:
        current_datetime = get_time_setting_tz()
    else:
        current_datetime = datetime.fromisoformat(current_datetime)
    cell = None

    if panel_id:
        get_mode = request.GET.get('mode', None)

        panel = get_filter_panels(name_panel=panel_id).first()
        if panel:
            try:
                cell = Cell.objects.get(panel=panel)
            except Cell.DoesNotExist:
                cell = None
        if get_mode == 'send':
            get_target = request.GET.get('target', None)
            description = f'Перемещен в {get_target}'
            q_panels_change_department(id_panel=panel_id, new_department=get_target, comment=comment,
                                       description=description,
                                       type_report='moving', user=user)
        elif get_mode == 'add_service_comment':
            PanelHistoryReport.objects.create(panel=Panels.objects.get(name=panel_id),
                                              description=comment,
                                              type_report='service', user=user, comment=f'добавлен вручную',
                                              time=current_datetime)
        elif get_mode == 'add_breakdown_comment':
            PanelHistoryReport.objects.create(panel=Panels.objects.get(name=panel_id),
                                              description=comment,
                                              type_report='breakdown', user=user, comment=f'добавлен вручную',
                                              time=current_datetime)

        panel_report_history = get_formated_panel_history_report(id_panel=panel)

        panel_info = {'id': panel.name, 'display': panel.display, 'comment': panel.comment,
                      'department': panel.department,
                      'condition': panel.condition, 'application_status': panel.application_status}
    else:
        panel_report_history = None
        panel_info = dict(id=None, display=None, comment=None, department=None, condition=None, application_status=None)
    if input_id and input_model:
        x = {'kolizey': 'KLZ',
             'shk': 'SHK',
             'belinskogo': 'BLN',
             'malkova': 'MLK'}
        try:
            Panels.objects.create(name=f'{x[input_model]}-{input_id}', display=Display.objects.get(name=input_model),
                                  condition=Condition.objects.get(name='work'),
                                  department=Department.objects.get(name='zip'),
                                  application_status=ApplicationStatus.objects.get(name='default'), comment=comment)
        except:
            pass

    filtered_models = [{"display_name": 'kolizey', "name": "KLZ", "selected": False},
                       {"display_name": 'malkova', "name": "MLK", "selected": False},
                       {"display_name": 'shk', "name": "SHK", "selected": False},
                       {"display_name": 'belinskogo', "name": "BLN", "selected": False}]
    for model_type in filtered_models:
        model_type['selected'] = f"model_type_{model_type['name']}" in request.POST
    list_of_filtered_models = [x['display_name'] for x in filtered_models if x['selected']]
    if not list_of_filtered_models:
        list_of_filtered_models = [x['display_name'] for x in filtered_models]

    hubs = Hubs.objects.all()
    wires = Wires.objects.all()
    lamels = Lamels.objects.all()
    # снизу временное решение перед презенатцией, потмо нужно убрать эту заглушку
    new_list_of_filtered_models = list_of_filtered_models
    if display_name:
        new_list_of_filtered_models = [display_name]
    context = {'panel_report_history': panel_report_history,
               'display_name': display_name,
               'hubs': hubs,
               'wires': wires,
               'lamels': lamels,
               'filtered_models': filtered_models,
               'list_of_filtered_models': new_list_of_filtered_models,
               'panel': panel_info,
               'cell': cell,
               'panels_db': panels,
               'title': 'ЗИП',
               'department': 'zip'}
    return render(request, 'zip/zip.html', context)


@login_required
def search(request, id_panel=None):
    return render(request, 'zip/zip.html')


@login_required
def add(request, id_panel=None):
    return render(request, 'zip/zip.html')


@login_required
def dell(request, id_panel=None):
    return render(request, 'zip/zip.html')
