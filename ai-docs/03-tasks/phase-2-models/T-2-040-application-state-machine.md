# T-2-040. `ApplicationStateMachine` + `Transition` декларативно

> **Тип:** refactor / architecture
> **Приоритет:** P0 (ключ Фазы 2)
> **Оценка:** 3 часа
> **Фаза:** 2
> **Статус:** done

---

## Цель

Переписать 150 строк ветвлений `apply_application()` в декларативную FSM. Каждый переход — объект `Transition`, с правами, валидацией, обязательными полями.

Даёт:
- Предсказуемость: переходы явно перечислены, невалидные физически невозможны
- Простоту тестов: одна параметризация покрывает все переходы
- Авторизацию: в transition зашиты права (кто может выполнять)
- API-friendly: `/applications/<id>/transition` принимает `target` — машина решает

---

## Зависимости

- **Блокируется:** T-2-014, T-2-020 (ApplicationEvent), T-2-022 (ActivityLog), T-2-003 (regression тесты)
- **Блокирует:** T-2-021 (удаление старых полей), Фаза 3 (API)

---

## Целевой дизайн

### Структура

```
apps/workflow/applications/
├── state_machine.py        # сам FSM
├── transitions.py          # список Transition-объектов
├── services.py             # ApplicationService.transition() — фасад
├── exceptions.py           # InvalidTransition, TransitionRequired, etc
```

### `Transition` — dataclass

```python
# apps/workflow/applications/state_machine.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable

from apps.workflow.applications.models import Application, ApplicationStatus


@dataclass(frozen=True)
class Transition:
    """Декларативное описание перехода состояния заявки."""
    
    name: str                                # 'apply_in_control' — имя самого перехода
    from_state: str                          # 'sent_to_control'
    to_state: str                            # 'apply_in_control'
    event_type: str                          # 'control_applied' — что записать в ApplicationEvent
    
    # Требования к исполнителю
    allowed_permissions: tuple[str, ...] = ()  # ('control', 'admin', 'all')
    
    # Требования к payload
    required_fields: tuple[str, ...] = ()      # ('comment',) — обязательно
    optional_fields: tuple[str, ...] = ()      # ('file', 'executor_id')
    
    # Дополнительная проверка (опц.)
    validator: Callable[[Application, dict], None] | None = None


# --- Registry ---
TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        name='control_apply',
        from_state='sent_to_control',
        to_state='apply_in_control',
        event_type='control_applied',
        allowed_permissions=('control', 'admin', 'all'),
        optional_fields=('comment',),
    ),
    Transition(
        name='control_send_to_service',
        from_state='apply_in_control',
        to_state='sent_to_service',
        event_type='sent_to_service',
        allowed_permissions=('control', 'admin', 'all'),
        optional_fields=('comment', 'executor_id'),
    ),
    Transition(
        name='service_apply',
        from_state='sent_to_service',
        to_state='work_in_service',
        event_type='service_applied',
        allowed_permissions=('service', 'admin', 'all'),
        optional_fields=('comment',),
    ),
    Transition(
        name='service_complete',
        from_state='work_in_service',
        to_state='done',
        event_type='work_completed',
        allowed_permissions=('service', 'admin', 'all'),
        optional_fields=('comment', 'file'),
    ),
    Transition(
        name='service_unable',
        from_state='work_in_service',
        to_state='unable',
        event_type='work_unable',
        allowed_permissions=('service', 'admin', 'all'),
        required_fields=('comment',),  # ВАЖНО: причину невозможности — обязательно
    ),
    Transition(
        name='archive_done',
        from_state='done',
        to_state='archive_done',
        event_type='archived',
        allowed_permissions=('control', 'service', 'admin', 'all'),
        optional_fields=('comment',),
    ),
    Transition(
        name='archive_unable',
        from_state='unable',
        to_state='archive_unable',
        event_type='archived',
        allowed_permissions=('control', 'service', 'admin', 'all'),
        optional_fields=('comment',),
    ),
)
```

### `ApplicationStateMachine` — проверяющий

```python
# apps/workflow/applications/state_machine.py (продолжение)

from apps.workflow.applications.exceptions import (
    InvalidTransition, TransitionRequired, TransitionPermissionDenied,
)


class ApplicationStateMachine:
    """Проверяет и выполняет переходы по декларации TRANSITIONS."""
    
    def __init__(self, transitions=TRANSITIONS):
        self._transitions = transitions
        self._by_name = {t.name: t for t in transitions}
        self._by_pair = {(t.from_state, t.to_state): t for t in transitions}
    
    def get_by_name(self, name: str) -> Transition:
        if name not in self._by_name:
            raise InvalidTransition(code='unknown_transition', message=f'Transition {name} not defined')
        return self._by_name[name]
    
    def get_allowed_from(self, state: str) -> list[Transition]:
        """Список возможных переходов из текущего состояния."""
        return [t for t in self._transitions if t.from_state == state]
    
    def check(self, transition: Transition, application: Application, user, payload: dict) -> None:
        """Полная проверка. Бросает исключения если что-то не так."""
        # 1. Состояние совпадает
        if application.status.name != transition.from_state:
            raise InvalidTransition(
                code='wrong_state',
                message=f'Заявка в {application.status.name}, ожидалось {transition.from_state}'
            )
        
        # 2. Права
        user_permission = getattr(user, 'permission', None)
        if transition.allowed_permissions and user_permission not in transition.allowed_permissions:
            raise TransitionPermissionDenied(
                code='forbidden_for_role',
                message=f'У {user.username} нет права выполнить {transition.name}'
            )
        
        # 3. Обязательные поля
        for field_name in transition.required_fields:
            if field_name not in payload or not payload[field_name]:
                raise TransitionRequired(
                    code='required_field_missing',
                    message=f'Для {transition.name} обязательно поле {field_name}'
                )
        
        # 4. Кастомная валидация
        if transition.validator:
            transition.validator(application, payload)


state_machine = ApplicationStateMachine()
```

### `ApplicationService.transition()` — фасад

```python
# apps/workflow/applications/services.py
from django.db import transaction
from django.utils import timezone
import structlog

from apps.activity.services import activity_logger
from apps.workflow.applications.models import Application, ApplicationStatus, ApplicationEvent
from apps.workflow.applications.state_machine import state_machine

logger = structlog.get_logger(__name__)


class ApplicationService:
    def transition(
        self,
        *,
        application_id: int,
        transition_name: str,
        user,
        comment: str = '',
        file=None,
        executor_id: int | None = None,
    ) -> Application:
        """Выполнить переход. Всё в одной транзакции."""
        
        transition = state_machine.get_by_name(transition_name)
        
        payload = {'comment': comment, 'file': file, 'executor_id': executor_id}
        
        with transaction.atomic():
            app = Application.objects.select_for_update().get(pk=application_id)
            state_machine.check(transition, app, user, payload)
            
            # Обновить статус
            new_status = ApplicationStatus.objects.get(name=transition.to_state)
            app.status = new_status
            app.last_update_date_time = timezone.now()
            if executor_id:
                app.executor_id = executor_id
            app.save()
            
            # Записать событие
            event = ApplicationEvent.objects.create(
                application=app,
                event_type=transition.event_type,
                actor_username=user.username,
                actor_id=user.id,
                occurred_at=timezone.now(),
                comment=comment,
                file=file,
                state_from=transition.from_state,
                state_to=transition.to_state,
                payload={'executor_id': executor_id} if executor_id else {},
            )
            
            # И в общий журнал
            def _log_after_commit():
                activity_logger.log(
                    event_type='application.transitioned',
                    target=app,
                    actor=user,
                    description=f'{transition.from_state} → {transition.to_state}',
                    comment=comment,
                    payload={
                        'transition': transition.name,
                        'application_id': app.id,
                        'event_id': event.id,
                    },
                )
                # TODO: эмитим NotificationEvent здесь же (T-5-xxx)
            
            transaction.on_commit(_log_after_commit)
            
            logger.info('application_transitioned',
                        application_id=app.id,
                        from_state=transition.from_state,
                        to_state=transition.to_state,
                        actor=user.username)
        
        return app


application_service = ApplicationService()
```

### Exceptions

```python
# apps/workflow/applications/exceptions.py
from shared.exceptions import DomainError

class InvalidTransition(DomainError):
    code = 'invalid_state_transition'

class TransitionRequired(DomainError):
    code = 'required_field_missing'

class TransitionPermissionDenied(DomainError):
    code = 'forbidden_for_role'
```

### Compat-shim для legacy

`application/utils.py`:
```python
"""Compat shim."""
from apps.workflow.applications.services import application_service

def apply_application(application_id, target_status, user, comment='', **kwargs):
    """Legacy wrapper. Переводит заявку в target_status."""
    # target_status — это to_state, находим transition
    from apps.workflow.applications.state_machine import state_machine
    app = Application.objects.get(pk=application_id)
    transitions = state_machine.get_allowed_from(app.status.name)
    transition = next((t for t in transitions if t.to_state == target_status), None)
    if not transition:
        from .exceptions import InvalidTransition
        raise InvalidTransition(code='invalid_transition',
                                message=f'No transition from {app.status.name} to {target_status}')
    
    return application_service.transition(
        application_id=application_id,
        transition_name=transition.name,
        user=user,
        comment=comment,
        **kwargs,
    )
```

---

## Тесты

Параметризованный test для всех 7 переходов + негативные сценарии (см. T-2-003 как baseline).

```python
# apps/workflow/applications/tests/test_state_machine.py
import pytest
from apps.workflow.applications.services import application_service
from apps.workflow.applications.state_machine import state_machine, TRANSITIONS

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('transition', TRANSITIONS, ids=lambda t: t.name)
def test_all_declared_transitions_execute(transition, application_factory, ms_user_factory, display_factory):
    display = display_factory(rows=2, cols=2)
    cell = display.cells.first()
    # Создать юзера с нужными permission'ами
    user = ms_user_factory(permission=transition.allowed_permissions[0] if transition.allowed_permissions else 'admin')
    
    app = application_factory(
        display=display, panel=cell.panel, cell=cell,
        status__name=transition.from_state,
    )
    # обязательные поля
    extra = {}
    if 'comment' in transition.required_fields:
        extra['comment'] = 'test'
    
    result = application_service.transition(
        application_id=app.id,
        transition_name=transition.name,
        user=user,
        **extra,
    )
    
    assert result.status.name == transition.to_state
    assert result.events.filter(event_type=transition.event_type).exists()


def test_transition_wrong_state_raises(application_factory, ms_user_factory):
    from apps.workflow.applications.exceptions import InvalidTransition
    user = ms_user_factory(permission='admin')
    app = application_factory(status__name='done')
    
    with pytest.raises(InvalidTransition):
        application_service.transition(
            application_id=app.id,
            transition_name='control_apply',  # не из done
            user=user,
        )


def test_transition_missing_required_raises(application_factory, ms_user_factory):
    from apps.workflow.applications.exceptions import TransitionRequired
    user = ms_user_factory(permission='service')
    app = application_factory(status__name='work_in_service')
    
    with pytest.raises(TransitionRequired):
        application_service.transition(
            application_id=app.id,
            transition_name='service_unable',  # требует comment
            user=user,
        )


def test_transition_without_permission_raises(application_factory, ms_user_factory):
    from apps.workflow.applications.exceptions import TransitionPermissionDenied
    user = ms_user_factory(permission='monitoring')  # не может делать control_apply
    app = application_factory(status__name='sent_to_control')
    
    with pytest.raises(TransitionPermissionDenied):
        application_service.transition(
            application_id=app.id,
            transition_name='control_apply',
            user=user,
        )


def test_transition_is_atomic(application_factory, ms_user_factory, monkeypatch):
    """Если что-то упадёт посреди transition — rollback, статус не изменён."""
    user = ms_user_factory(permission='admin')
    app = application_factory(status__name='sent_to_control')
    original_status = app.status.name
    
    from apps.workflow.applications import services
    def boom(*args, **kwargs):
        raise RuntimeError('simulated')
    monkeypatch.setattr(services.ApplicationEvent.objects, 'create', boom)
    
    with pytest.raises(RuntimeError):
        application_service.transition(
            application_id=app.id,
            transition_name='control_apply',
            user=user,
        )
    
    app.refresh_from_db()
    assert app.status.name == original_status  # rollback сработал
```

---

## Критерии приёмки

- [ ] `state_machine.py`, `transitions.py`, `services.py`, `exceptions.py` созданы
- [ ] Все 7 transition'ов из roadmap описаны декларативно
- [ ] `ApplicationStateMachine.check()` покрывает все 4 проверки
- [ ] `application_service.transition()` работает атомарно
- [ ] Events пишутся в `ApplicationEvent` + `ActivityLog`
- [ ] Legacy `apply_application()` — wrapper через новый сервис
- [ ] Параметризованные тесты покрывают все переходы
- [ ] Негативные тесты: wrong_state, missing_required, permission_denied, atomicity
- [ ] Coverage нового кода ≥ 85%
- [ ] `python manage.py check` — чисто
- [ ] Regression-тесты из T-2-003 — проходят (через wrapper)

---

## Что НЕ делать

- **НЕ оставляй** 150-строчный `apply_application()` — он становится тонким wrapper'ом
- **НЕ пиши** логику переходов в if-else — только в `TRANSITIONS` tuple
- **НЕ зови** `ActivityLog` / `NotificationService` из StateMachine.check() — это чистая валидация
- **НЕ зови** service напрямую из шаблонов — через view/API

---

## Next

После этой задачи:
- **T-2-021** (удалить 28 старых полей) — разблокируется, потому что новый service пишет только в ApplicationEvent
- **T-3-014** (API transition endpoint) — становится тривиальным: `POST /applications/<id>/transition { transition_name, comment }` → service → 200
