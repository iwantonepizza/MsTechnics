from django import template
from django.utils.http import urlencode

from application.models import ApplicationStatus
from core_mechanic.Data.Db.orm_query import get_display_at_city
from main.models import Condition

register = template.Library()
from zip.models import Panels, Cell


@register.simple_tag()
def get_allowed_status(excluded_name: str = None):
    if excluded_name:
        return Condition.objects.exclude(name=excluded_name)
    return Condition.objects.all()


@register.simple_tag(takes_context=True)
def update_get_query(context, **kwargs):
    query = context['request'].GET.dict()
    query.update(kwargs)
    return urlencode(query)


@register.simple_tag()
def get_work_monitor_tag(city_name):
    return get_display_at_city(city_name)


@register.simple_tag()
def qtag_department(department_name: str = None, panels_filter: list = None, model_filter: list = None,
                    condition_filter: list = None):
    queryset = Panels.objects.select_related('department', 'display', 'condition__icon')
    if department_name:
        queryset = queryset.filter(
            department__name=department_name
        )
    # Если panels_filter не пуст, применяем дополнительную фильтрацию
    if panels_filter:
        queryset = queryset.filter(name__in=panels_filter)
    if condition_filter:
        queryset = queryset.filter(condition__name__in=condition_filter)
    if model_filter:
        queryset = queryset.filter(display__name__in=model_filter)
    # Получаем значения
    res = queryset.values(
        'name', 'display__name', 'comment', 'condition__icon__smile_icon'
    )

    # Конвертация имен ключей для удобства

    res = [
        {
            'name': item['name'],
            'display': item['display__name'],
            'comment': item['comment'],
            'icon': item['condition__icon__smile_icon']
        }
        for item in res
    ]
    return res


@register.simple_tag()
def application_status_info():
    return ApplicationStatus.objects.select_related('color').all()


@register.simple_tag()
def get_cell(panel: Panels = None):
    cell = Cell.objects.filter(panel=panel)
    if cell:
        return cell.first().position()
    else:
        return "xxx"
