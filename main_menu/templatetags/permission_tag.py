from django import template
from project_config.settings import ALLOWED_DEPARTMENT

from apps.core.users.models import MsUser

register = template.Library()


@register.simple_tag()
def check_city_permission(user_id: str, city_id: str) -> bool | None:
    """Проверка на доступ юзера к городу.
    Принимает id, отправляет True если можно, False если нет доступа. None если ошибка"""
    try:
        user = MsUser.objects.get(id=user_id)
        user_cities = user.allowed_city.all()  # Получаем Queryset всех городов
        user_access = any(city.id == city_id for city in user_cities)
        return user_access
    except Exception:
        return None


@register.simple_tag()
def get_allowed_department():
    return ALLOWED_DEPARTMENT
