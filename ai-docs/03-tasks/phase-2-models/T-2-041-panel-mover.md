# T-2-041. `PanelMover` — сервис перемещения панелей

> **Тип:** refactor / feature
> **Приоритет:** P1
> **Оценка:** 2 часа
> **Фаза:** 2
> **Статус:** done
> **User task:** #8 (блокировка перевода с активной заявкой)

---

## Цель

Вынести логику «переместить панель между отделами» (`monitor ↔ service ↔ zip ↔ hand`) в отдельный сервис. Сейчас эта логика размазана по `zip/views.py::panel_change_department`, `main/Db/orm_query.py` и ещё нескольким местам.

Вместе с этим — закрыть задачу владельца #8: **нельзя отправить в ЗИП/сервис панель с активной заявкой**.

---

## Зависимости

- **Блокируется:** T-2-013 (Panel), T-2-022 (ActivityLog)

---

## Целевой дизайн

### Сервис

```python
# apps/directory/panels/services.py
from __future__ import annotations
from django.db import transaction
from django.utils import timezone
import structlog

from apps.activity.services import activity_logger
from apps.directory.panels.models import Panel, Department
from shared.exceptions import PanelHasActiveApplication

logger = structlog.get_logger(__name__)


class PanelMover:
    """Перемещение панели между отделами с валидацией."""
    
    # Допустимые переходы (если нужны ограничения). Пока разрешаем всё между service/zip/hand.
    # monitor — нельзя напрямую, только через assign_to_cell (установить в экран).
    DIRECT_TRANSFERS = {
        ('service', 'zip'),
        ('service', 'hand'),
        ('zip', 'service'),
        ('zip', 'hand'),
        ('hand', 'service'),
        ('hand', 'zip'),
        # monitor → service: через remove_from_cell (другой сервис)
        ('monitor', 'service'),  # допустим для случая снятия без смены cell
        ('monitor', 'zip'),
    }
    
    def move_to_department(
        self,
        *,
        panel: Panel,
        to_department_name: str,
        actor,
        comment: str = '',
    ) -> Panel:
        """Переместить панель в другой отдел.
        
        Raises:
            PanelHasActiveApplication: если у панели есть активная заявка
            ValueError: если переход недопустим
        """
        from_dept = panel.department.name
        
        # 1. Проверка на активную заявку
        #    ПРИЧИНА: задача владельца #8 — не дать увести панель
        #    когда по ней ведётся работа
        if panel.active_application:  # property из T-2-028
            raise PanelHasActiveApplication(
                code='panel_has_active_application',
                message=f'У панели {panel.name} есть активная заявка '
                        f'ID-{panel.active_application.id}. Сначала закройте её.',
                panel_id=panel.name,
                application_id=panel.active_application.id,
            )
        
        # 2. Проверка допустимости перехода
        if (from_dept, to_department_name) not in self.DIRECT_TRANSFERS:
            raise ValueError(
                f'Недопустимый переход: {from_dept} → {to_department_name}. '
                f'Используй assign_to_cell / remove_from_cell для установки в экран.'
            )
        
        with transaction.atomic():
            to_dept = Department.objects.get(name=to_department_name)
            old_dept_name = panel.department.name
            
            panel.department = to_dept
            panel.save(update_fields=['department'])
            
            # Если панель стояла в ячейке — снимаем
            if hasattr(panel, 'cell_set'):  # Panel может быть в Cell через related
                cells = panel.cell_set.all()
                for cell in cells:
                    cell.panel = None
                    cell.save(update_fields=['panel'])
            
            def _log_after_commit():
                activity_logger.log(
                    event_type='panel.moved',
                    target=panel,
                    actor=actor,
                    description=f'{old_dept_name} → {to_department_name}',
                    comment=comment,
                    payload={
                        'from_department': old_dept_name,
                        'to_department': to_department_name,
                    },
                )
            transaction.on_commit(_log_after_commit)
            
            logger.info('panel_moved',
                        panel_name=panel.name,
                        from_dept=old_dept_name,
                        to_dept=to_department_name,
                        actor=getattr(actor, 'username', None))
        
        return panel
    
    def assign_to_cell(
        self,
        *,
        panel: Panel,
        cell,
        actor,
        comment: str = '',
    ) -> Panel:
        """Установить панель в ячейку. Автоматически меняет department → monitor."""
        if cell.panel is not None and cell.panel != panel:
            raise ValueError(f'В ячейке уже стоит панель {cell.panel.name}')
        
        if panel.active_application:
            raise PanelHasActiveApplication(
                message=f'У панели {panel.name} активная заявка — нельзя устанавливать в экран'
            )
        
        with transaction.atomic():
            monitor_dept = Department.objects.get(name='monitor')
            old_dept_name = panel.department.name
            
            cell.panel = panel
            cell.save(update_fields=['panel'])
            
            panel.department = monitor_dept
            panel.save(update_fields=['department'])
            
            def _log_after_commit():
                activity_logger.log(
                    event_type='display.panel_installed',
                    target=cell.display,
                    actor=actor,
                    description=f'⬇️ {panel.name} → {cell.position}',
                    comment=comment,
                    payload={
                        'panel_name': panel.name,
                        'cell_id': cell.id,
                        'from_department': old_dept_name,
                    },
                )
                activity_logger.log(
                    event_type='panel.moved',
                    target=panel,
                    actor=actor,
                    description=f'{old_dept_name} → monitor · {cell.display.name} {cell.position}',
                    comment=comment,
                    payload={
                        'from_department': old_dept_name,
                        'to_department': 'monitor',
                        'cell_id': cell.id,
                    },
                )
            transaction.on_commit(_log_after_commit)
        
        return panel
    
    def remove_from_cell(
        self,
        *,
        cell,
        to_department_name: str,  # 'service' или 'zip'
        actor,
        comment: str = '',
    ) -> Panel | None:
        """Снять панель из ячейки, отправить в указанный отдел."""
        if cell.panel is None:
            raise ValueError(f'В ячейке {cell.position} нет панели')
        
        panel = cell.panel
        if panel.active_application:
            raise PanelHasActiveApplication(
                message=f'У панели {panel.name} активная заявка — сначала закройте её'
            )
        
        with transaction.atomic():
            target_dept = Department.objects.get(name=to_department_name)
            display = cell.display
            
            cell.panel = None
            cell.save(update_fields=['panel'])
            
            panel.department = target_dept
            panel.save(update_fields=['department'])
            
            def _log_after_commit():
                activity_logger.log(
                    event_type='display.panel_removed',
                    target=display,
                    actor=actor,
                    description=f'⬆️ {panel.name} из {cell.position} → {to_department_name}',
                    comment=comment,
                    payload={
                        'panel_name': panel.name,
                        'cell_id': cell.id,
                        'to_department': to_department_name,
                    },
                )
                activity_logger.log(
                    event_type='panel.moved',
                    target=panel,
                    actor=actor,
                    description=f'monitor → {to_department_name}',
                    comment=comment,
                    payload={
                        'from_department': 'monitor',
                        'to_department': to_department_name,
                        'cell_id_was': cell.id,
                    },
                )
            transaction.on_commit(_log_after_commit)
        
        return panel


panel_mover = PanelMover()
```

### Exception (в `shared/exceptions.py` уже добавлено в T-2-011)

```python
class PanelHasActiveApplication(DomainError):
    """Нельзя выполнить действие — у панели активная заявка."""
    code = 'panel_has_active_application'
```

### Compat-shim для legacy

Легаси view `panel_change_department` в `zip/views.py`:
```python
# было:
def panel_change_department(request):
    panel_id = request.POST['panel_id']
    new_department = request.POST['target_department']
    panel = Panels.objects.get(id=panel_id)
    # 30 строк логики, без проверки на активные заявки
    panel.department = Department.objects.get(name=new_department)
    panel.save()
    # лог в HistoryReport
    return safe_redirect(request)


# стало:
from apps.directory.panels.services import panel_mover
from shared.exceptions import PanelHasActiveApplication

def panel_change_department(request):
    panel_id = request.POST['panel_id']
    new_department = request.POST['target_department']
    panel = Panel.objects.get(id=panel_id)
    comment = request.POST.get('comment', '')
    
    try:
        panel_mover.move_to_department(
            panel=panel,
            to_department_name=new_department,
            actor=request.user,
            comment=comment,
        )
        messages.success(request, f'Панель {panel.name} → {new_department}')
    except PanelHasActiveApplication as e:
        messages.error(request, str(e))
    except ValueError as e:
        messages.error(request, str(e))
    
    return safe_redirect(request)
```

### UI блокировка (legacy шаблон)

В `panel_info_block.html` (есть уже, см. template в проекте) — показать disabled кнопку если активная заявка:
```django
{% if panel.active_application %}
    <a class="head-button disabled"
       title="Нельзя переместить — активная заявка ID-{{ panel.active_application.id }}"
       style="opacity: 0.5; cursor: not-allowed">
        📄
    </a>
{% else %}
    <a class="head-button open-modal" data-api-url="/zip/modal-panel-change-department/" ...>📄</a>
{% endif %}
```

В SPA это будет делаться через `button[disabled]` + tooltip (Фаза 4).

---

## Тесты

```python
# apps/directory/panels/tests/test_panel_mover.py
import pytest
from apps.directory.panels.services import panel_mover
from shared.exceptions import PanelHasActiveApplication

pytestmark = pytest.mark.django_db


def test_move_to_department_success(panels_factory, ms_user_factory, department_factory):
    panel = panels_factory(department__name='service')
    user = ms_user_factory(permission='admin')
    
    result = panel_mover.move_to_department(
        panel=panel,
        to_department_name='zip',
        actor=user,
        comment='перевозка',
    )
    
    result.refresh_from_db()
    assert result.department.name == 'zip'


def test_move_blocked_by_active_application(panels_factory, application_factory, ...):
    panel = panels_factory(department__name='service')
    application_factory(panel=panel, status__name='work_in_service')
    user = ms_user_factory(permission='admin')
    
    with pytest.raises(PanelHasActiveApplication) as exc:
        panel_mover.move_to_department(
            panel=panel, to_department_name='zip', actor=user,
        )
    assert exc.value.code == 'panel_has_active_application'
    
    panel.refresh_from_db()
    assert panel.department.name == 'service'  # не изменилось


def test_move_invalid_transition_raises(panels_factory, ms_user_factory):
    panel = panels_factory(department__name='monitor')
    user = ms_user_factory()
    # monitor → hand — не в DIRECT_TRANSFERS (monitor → service ok, но monitor → hand нет)
    with pytest.raises(ValueError):
        panel_mover.move_to_department(panel=panel, to_department_name='hand', actor=user)


def test_assign_to_cell_changes_department_to_monitor(panels_factory, display_factory, ms_user_factory):
    panel = panels_factory(department__name='zip')
    display = display_factory(rows=2, cols=2)
    empty_cell = [c for c in display.cells.all() if c.panel is None][0]
    user = ms_user_factory()
    
    panel_mover.assign_to_cell(panel=panel, cell=empty_cell, actor=user)
    
    panel.refresh_from_db()
    empty_cell.refresh_from_db()
    assert panel.department.name == 'monitor'
    assert empty_cell.panel == panel


def test_remove_from_cell_with_application_blocked(display_factory, application_factory, ms_user_factory):
    display = display_factory(rows=2, cols=2)
    cell = display.cells.first()
    application_factory(panel=cell.panel, cell=cell, status__name='sent_to_service')
    user = ms_user_factory()
    
    with pytest.raises(PanelHasActiveApplication):
        panel_mover.remove_from_cell(
            cell=cell, to_department_name='service', actor=user,
        )


def test_activity_log_written_on_move(panels_factory, ms_user_factory):
    from apps.activity.models import ActivityLog
    panel = panels_factory(department__name='zip')
    user = ms_user_factory(username='mover')
    
    panel_mover.move_to_department(panel=panel, to_department_name='service', actor=user)
    
    # Проверяем что лог записан (после commit — транзакция закрыта в тесте)
    log = ActivityLog.objects.filter(
        event_type='panel.moved',
        target_object_id=panel.name,
    ).first()
    assert log is not None
    assert log.actor_username == 'mover'
    assert log.payload['from_department'] == 'zip'
    assert log.payload['to_department'] == 'service'
```

---

## Критерии приёмки

- [ ] `PanelMover` сервис реализован со всеми тремя методами (`move_to_department`, `assign_to_cell`, `remove_from_cell`)
- [ ] Все три метода проверяют `panel.active_application` → `PanelHasActiveApplication`
- [ ] ActivityLog записывается после commit (через `on_commit`)
- [ ] Legacy `panel_change_department` view → использует сервис
- [ ] В шаблоне кнопка «В ЗИП / В сервис» disabled при активной заявке
- [ ] Unit-тесты покрывают happy path + блокировку + invalid transition + атомарность (минимум 6 тестов)
- [ ] Coverage нового кода ≥ 85%

---

## Что НЕ делать

- **НЕ забудь** `select_for_update()` — панель может двигаться параллельно, нужен row-lock
- **НЕ пиши** бизнес-логику напрямую в views — только вызов сервиса
- **НЕ логируй** до commit — тогда лог может быть, а панель не переехала

---

## Next

После этой задачи у нас полностью готовый backend под Фазу 3 (API): service-layer + FSM + activity log + normalized models. Фаза 3 = тонкий API-слой сверху.
