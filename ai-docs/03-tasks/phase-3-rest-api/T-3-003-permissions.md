# T-3-003. Permissions: роли + допуск по городам

> **Тип:** core
> **Приоритет:** P0
> **Оценка:** 2 часа
> **Фаза:** 3
> **Статус:** done

---

## Цель

Единая permission-инфраструктура. Все view'ы Фазы 3 пользуются ею. Нельзя писать `IsAuthenticated` где попало — должны быть точные правила вроде `HasDepartmentAccess('control')`, `HasCityAccess(display.city_id)`.

---

## Зависимости

- **Блокируется:** T-3-001
- **Блокирует:** все CRUD-задачи (T-3-010..T-3-041)

---

## Что нужно сделать

### Шаг 1. `shared/permissions.py`

```python
"""
Стандартные permission-классы для DRF.

Использование:
    permission_classes = [IsAuthenticated, HasDepartmentAccess('control')]
    
Или комбинация:
    permission_classes = [IsAuthenticated, ReadOnlyForMonitoring, HasCityAccess]
"""
from __future__ import annotations
from typing import Iterable

from rest_framework.permissions import BasePermission, SAFE_METHODS

# Department permissions, синхронизированные с MsUser.permission choices
DEPARTMENT_ALL    = 'all'        # доступ ко всему
DEPARTMENT_ADMIN  = 'admin'      # суперпользователь
DEPARTMENT_MON    = 'monitoring'
DEPARTMENT_CTRL   = 'control'
DEPARTMENT_SVC    = 'service'
DEPARTMENT_TECH   = 'technical'
DEPARTMENT_NONE   = 'none_type'  # ничего не видит


class HasDepartmentAccess(BasePermission):
    """
    Доступ к view есть, если permission юзера в одном из перечисленных или 'all'/'admin'.
    
    Параметризованный класс — используй как фабрику:
        permission_classes = [HasDepartmentAccess.for_('control', 'admin')]
    """
    required_departments: tuple[str, ...] = ()

    @classmethod
    def for_(cls, *departments: str):
        """Создаёт subclass с конкретными департаментами."""
        return type(
            f'{cls.__name__}_{"_".join(departments)}',
            (cls,),
            {'required_departments': tuple(departments)},
        )

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        perm = getattr(request.user, 'permission', None)
        if perm in (DEPARTMENT_ALL, DEPARTMENT_ADMIN):
            return True
        return perm in self.required_departments


class HasCityAccess(BasePermission):
    """
    Object-level permission: проверяет что у юзера есть доступ к городу объекта.
    
    Объект должен иметь .city (Display) или .display.city (Cell, Panel)
    или .panel.display.city (Application).
    """
    
    def has_permission(self, request, view) -> bool:
        # general check — пускаем, дальше через has_object_permission
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        if user.permission in (DEPARTMENT_ALL, DEPARTMENT_ADMIN):
            return True
        
        city_id = self._extract_city_id(obj)
        if city_id is None:
            # объект без города — пускаем (например, справочник)
            return True
        
        # MsUser.allowed_city — M2M
        return user.allowed_city.filter(id=city_id).exists()
    
    @staticmethod
    def _extract_city_id(obj) -> int | None:
        """Извлекает city_id из любой типичной модели."""
        if hasattr(obj, 'city_id'):
            return obj.city_id
        if hasattr(obj, 'display'):
            return getattr(obj.display, 'city_id', None)
        if hasattr(obj, 'panel') and obj.panel is not None:
            return getattr(obj.panel.display, 'city_id', None)
        if hasattr(obj, 'cell') and obj.cell is not None:
            return getattr(obj.cell.display, 'city_id', None)
        return None


class ReadOnlyForRole(BasePermission):
    """
    Юзер с заданной ролью видит read-only, остальные роли — нормально.
    
    Использование:
        class MonitoringReadOnly(ReadOnlyForRole):
            role = 'monitoring'
    """
    role: str = ''

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.permission == self.role:
            return request.method in SAFE_METHODS
        return True


class IsAdmin(BasePermission):
    """Только admin/all."""
    
    def has_permission(self, request, view) -> bool:
        return (
            request.user.is_authenticated 
            and request.user.permission in (DEPARTMENT_ALL, DEPARTMENT_ADMIN)
        )


class CanCreateApplication(BasePermission):
    """Создавать заявки могут monitoring, control, all, admin."""
    
    ALLOWED = (DEPARTMENT_MON, DEPARTMENT_CTRL, DEPARTMENT_ALL, DEPARTMENT_ADMIN)
    
    def has_permission(self, request, view) -> bool:
        return (
            request.user.is_authenticated
            and request.user.permission in self.ALLOWED
        )


class CanTransitionApplication(BasePermission):
    """
    Object-level: проверяет что роль юзера может выполнить запрошенный transition.
    
    target_state приходит в request.data['target_state'].
    Маппинг разрешённых transition'ов — из ApplicationStateMachine.
    """
    
    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        if user.permission in (DEPARTMENT_ALL, DEPARTMENT_ADMIN):
            return True
        
        target = request.data.get('target_state', '')
        if not target:
            return False
        
        from apps.workflow.applications.state_machine import application_fsm
        try:
            transition = application_fsm.get_transition(obj.status.name, target)
        except Exception:
            return False
        
        return user.permission in transition.allowed_for
```

### Шаг 2. Тесты

`apps/interface/tests/test_permissions.py`:

```python
import pytest
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import NotAuthenticated

from shared.permissions import (
    HasDepartmentAccess, HasCityAccess, IsAdmin, CanCreateApplication,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def factory():
    return APIRequestFactory()


class TestHasDepartmentAccess:
    def test_admin_allowed(self, factory, ms_user_factory):
        user = ms_user_factory(permission='admin')
        request = factory.get('/')
        request.user = user
        perm = HasDepartmentAccess.for_('control')()
        assert perm.has_permission(request, None) is True
    
    def test_specific_role_allowed(self, factory, ms_user_factory):
        user = ms_user_factory(permission='control')
        request = factory.get('/')
        request.user = user
        perm = HasDepartmentAccess.for_('control')()
        assert perm.has_permission(request, None) is True
    
    def test_other_role_denied(self, factory, ms_user_factory):
        user = ms_user_factory(permission='monitoring')
        request = factory.get('/')
        request.user = user
        perm = HasDepartmentAccess.for_('control')()
        assert perm.has_permission(request, None) is False
    
    def test_anon_denied(self, factory):
        request = factory.get('/')
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        perm = HasDepartmentAccess.for_('control')()
        assert perm.has_permission(request, None) is False


class TestHasCityAccess:
    def test_user_with_allowed_city_passes(self, factory, ms_user_factory, display_factory):
        display = display_factory()
        user = ms_user_factory(permission='control')
        user.allowed_city.add(display.city)
        request = factory.get('/')
        request.user = user
        perm = HasCityAccess()
        assert perm.has_object_permission(request, None, display) is True
    
    def test_user_without_city_blocked(self, factory, ms_user_factory, display_factory):
        display = display_factory()
        user = ms_user_factory(permission='control')
        # не добавляем allowed_city
        request = factory.get('/')
        request.user = user
        perm = HasCityAccess()
        assert perm.has_object_permission(request, None, display) is False
    
    def test_admin_bypass_city(self, factory, ms_user_factory, display_factory):
        display = display_factory()
        user = ms_user_factory(permission='admin')
        request = factory.get('/')
        request.user = user
        perm = HasCityAccess()
        assert perm.has_object_permission(request, None, display) is True


class TestCanTransitionApplication:
    def test_control_can_apply_transition(self, factory, ms_user_factory, application_factory):
        from apps.workflow.applications.models import Application
        app = application_factory(status__name='sent_to_control')
        user = ms_user_factory(permission='control')
        request = factory.post('/', {'target_state': 'apply_in_control'})
        request.user = user
        from shared.permissions import CanTransitionApplication
        perm = CanTransitionApplication()
        assert perm.has_object_permission(request, None, app) is True
    
    def test_monitoring_cannot_transition(self, factory, ms_user_factory, application_factory):
        app = application_factory(status__name='sent_to_control')
        user = ms_user_factory(permission='monitoring')
        request = factory.post('/', {'target_state': 'apply_in_control'})
        request.user = user
        from shared.permissions import CanTransitionApplication
        perm = CanTransitionApplication()
        assert perm.has_object_permission(request, None, app) is False
```

### Шаг 3. Документация в коде

В `shared/permissions.py` хорошие docstring'и обязательны (это API для всех будущих view'ов).

---

## Критерии приёмки

- [ ] `shared/permissions.py` создан
- [ ] Классы: `HasDepartmentAccess`, `HasCityAccess`, `ReadOnlyForRole`, `IsAdmin`, `CanCreateApplication`, `CanTransitionApplication`
- [ ] `HasDepartmentAccess.for_(*roles)` — фабричный метод работает
- [ ] Тесты на каждый класс, минимум по 3 сценария (admin, allowed, denied)
- [ ] Тесты coverage ≥ 90% для shared/permissions.py
- [ ] Docstrings на все публичные классы

---

## Что НЕ делать

- **НЕ кешируй** проверки в memcache/redis в этой задаче — преждевременная оптимизация
- **НЕ добавляй** group-permissions через Django auth — наш `MsUser.permission` (CharField) и `allowed_city` (M2M) — единственный источник правды
- **НЕ дублируй** логику в каждом view — одна точка правды

---

## Известные кейсы

- **Юзер с `permission='admin'`** проходит **всё**. Это законно.
- **Юзер с `permission='all'`** идентичен `admin` для целей permission. Используется кодом, который не различает их.
- **Юзер с `permission='none_type'`** — ничего не может (только просматривать /me). Полезно для отключённых аккаунтов без удаления.
