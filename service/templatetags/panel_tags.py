from django import template
from zip.models import Display
from django.utils.http import urlencode

from application.models import ApplicationStatus
from main.models import Condition

from zip.models import Panels

register = template.Library()


@register.simple_tag()
def get_allowed_status(excluded_name: str = None):
    """Это что не понмю"""
    if excluded_name:
        return Condition.objects.exclude(name=excluded_name)
    return Condition.objects.all()


@register.simple_tag(takes_context=True)
def update_get_query(context, **kwargs):
    query = context['request'].GET.dict()
    query.update(kwargs)
    return urlencode(query)


@register.simple_tag()
def get_city_displays(city):
    return Display.objects.filter(city=city)


@register.simple_tag()
def qtg_get_panels(department_name: str = None, panels_filter: list = None, display_slug: list = None,
                   condition_filter: list = None, user=None):
    """кверисет по параметрам, может и не нужон"""
    user_cities = user.allowed_city.all()
    queryset = Panels.objects.select_related('department', 'display', 'condition__icon', 'application_status', ).filter(
        display__city__in=user_cities)
    if department_name:
        queryset = queryset.filter(
            department__name=department_name
        )
    # Если panels_filter не пуст, применяем дополнительную фильтрацию
    if panels_filter:
        queryset = queryset.filter(name__in=panels_filter)
    if condition_filter:
        queryset = queryset.filter(condition__name__in=condition_filter)
    if display_slug:
        queryset = queryset.filter(display__slug__in=display_slug)

    return queryset


@register.simple_tag()
def application_status_info():
    return ApplicationStatus.objects.select_related('color').all()
