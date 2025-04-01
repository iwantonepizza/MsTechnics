from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages

from get_time import get_time_setting_tz
from main.models import Department
from main_menu.models import PanelHistoryReport
from zip.models import Panels, Lamels, Hubs, Display, Wires, PhotoDisplay
from main.Db.orm_query import get_formated_panel_history_report
import os
import json
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect


def upload_display_photos(request):
    if request.method == "POST":
        display_id = request.POST['display_id']
        display = get_object_or_404(Display, id=display_id)
        files = request.FILES.getlist('photo')  # Получаем список файлов
        for file in files:
            PhotoDisplay.objects.create(display=display, image=file,
                                        uploaded_at=get_time_setting_tz())  # Создаем фото

        return redirect(request.META['HTTP_REFERER'])
    else:
        return redirect(request.META['HTTP_REFERER'])


def delete_display_photos(request, photo_id):
    photo = get_object_or_404(PhotoDisplay, id=photo_id)
    photo.delete()  # Удаляем фото
    return JsonResponse({"message": "Фото удалено"}, status=200)


def get_display_photos(request, display_id):
    try:
        photos = PhotoDisplay.objects.filter(display_id=display_id)
        data = {"photos": [{"id": p.id, "name": p.image.name, "url": p.image.url} for p in photos]}
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=400)


@login_required
def index(request, display_slug='all', panel_id=None):
    user = request.user
    if panel_id:
        panel = Panels.objects.get(pk=panel_id)
    else:
        panel = None

    if panel:
        panel_report_history = get_formated_panel_history_report(PanelHistoryReport.objects.filter(panel=panel))
    else:
        panel_report_history = None

    if display_slug != 'all':
        filtered_displays = (display_slug,)
    else:
        filtered_displays = list(Display.objects.values_list('slug', flat=True))

    hubs = Hubs.objects.all()
    wires = Wires.objects.all()
    lamels = Lamels.objects.all()

    context = {
        'title': 'ЗИП',
        'department': 'zip',

        'hubs': hubs,
        'wires': wires,
        'lamels': lamels,

        'filtered_displays': filtered_displays,

        'panel_report_history': panel_report_history,
        'panel': panel,

    }
    return render(request, 'zip/zip.html', context)


@require_POST
def update_wires(request):
    try:
        updates = request.POST.getlist('updates[]')
        if not updates:
            return JsonResponse({'status': 'error', 'message': 'Нет данных для обновления'}, status=400)

        for update in updates:
            wire_id, new_count = update.split(':')
            wire_to_change = Wires.objects.get(id=wire_id)
            new_count = int(new_count)
            current_count = wire_to_change.count

            if new_count > current_count:
                wire_to_change.increase_count(new_count - current_count)
            elif new_count < current_count:
                wire_to_change.decrease_count(current_count - new_count)
            # Если new_count == current_count, ничего не делаем

        return JsonResponse({'status': 'success', 'message': 'Данные обновлены'})
    except Wires.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Объект не найден'}, status=404)
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': e.message}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ошибка сервера: {str(e)}'}, status=500)


@require_POST
def delete_photo(request):
    try:
        wire_id = request.POST.get('wire_id')
        wire_to_change = Wires.objects.get(id=wire_id)
        if wire_to_change.photo:
            if os.path.isfile(wire_to_change.photo.path):
                os.remove(wire_to_change.photo.path)
            wire_to_change.photo = None
            wire_to_change.save()
        return JsonResponse({'status': 'success', 'message': 'Фото удалено'})
    except Wires.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Объект не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ошибка: {str(e)}'}, status=500)


@require_POST
def update_photo(request):
    try:
        wire_id = request.POST.get('wire_id')
        wire_to_change = Wires.objects.get(id=wire_id)
        if 'photo' not in request.FILES:
            return JsonResponse({'status': 'error', 'message': 'Файл не передан'}, status=400)

        new_photo = request.FILES['photo']
        if wire_to_change.photo and os.path.isfile(wire_to_change.photo.path):
            os.remove(wire_to_change.photo.path)
        wire_to_change.photo = new_photo
        wire_to_change.save()
        return JsonResponse({'status': 'success', 'message': 'Фото обновлено', 'photo_url': wire_to_change.photo.url})

    except Wires.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Объект не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ошибка: {str(e)}'}, status=500)


@login_required
def add_panel_comment(request):
    """Создание репорта панели вручную"""
    if request.method == "POST":
        panel_id = request.POST.get("panel_id")
        comment = request.POST.get("comment")
        type_report = request.POST.get("type_report")
        user = request.user
        current_datetime = get_time_setting_tz()

        # Создание репорта в PanelHistoryReport
        PanelHistoryReport.objects.create(
            panel=Panels.objects.get(id=panel_id),
            description=f'✏️ {comment}',
            type_report=type_report,
            user=user.first_name,
            time=current_datetime,
            comment="добавлен вручную"
        )
        messages.success(request, f"Комментарий к панели {panel_id} добавлен")
        return redirect(request.META['HTTP_REFERER'])

    return redirect(request.META['HTTP_REFERER'])


@login_required()
def add_panel_comment_modal(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            return render(request, "modals/panel_comment.html", data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required()
def panel_info(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Загружаем JSON
            reports = PanelHistoryReport.objects.filter(panel__name=data['panel_name']).order_by('-time')
            data['reports'] = reports
            return render(request, "modals/panel_info.html", data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required()
def panel_remove_modal(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Загружаем JSON
            return render(request, "modals/panel_remove.html", data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)


@require_POST
def panel_change_department(request):
    try:
        panel_id = request.POST.get('target_panel_id', None)
        target_department = request.POST.get('target_department', None)
        comment = request.POST.get('comment', None)
        panel = Panels.objects.get(id=panel_id)
        department = Department.objects.get(name=target_department)
        panel.department = department
        panel.save()
        current_time = get_time_setting_tz()
        PanelHistoryReport.objects.create(panel=panel,
                                          description=f'❗️Перемещен: {department.description}',
                                          type_report='service', time=current_time, user=request.user, comment=comment)
        messages.success(request,f'Панель {panel.name} успешно перемещена в {department.description}!')
        return redirect(request.META['HTTP_REFERER'])
    except Department.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Имя конечного отдела не валидно'}, status=404)
    except Panels.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Айди панели не валиден'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ошибка в panel_change_department: {str(e)}'}, status=500)

@login_required()
def modal_panel_change_department(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            data['header'] = f'Перемещение в {data["target_department"]}'
            return render(request, "modals/confirm_change_department.html", data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)