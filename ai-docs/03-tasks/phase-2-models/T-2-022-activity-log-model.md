# T-2-022. Создать `ActivityLog` с GenericForeignKey

> **Тип:** migration / model
> **Приоритет:** P0 (ключ Фазы 2)
> **Оценка:** 2 часа
> **Фаза:** 2
> **Статус:** done

---

## Цель

Объединить 5 идентичных History-таблиц в одну нормализованную: `ActivityLog`.

Сейчас в проекте:
- `ApplicationHistoryReport` (application app)
- `PanelHistoryReport` + 4 типа (`moving`, `condition`, `breakdown`, `service`)
- `DisplayHistoryReport`

Все имеют практически одинаковую структуру: `description`, `comment`, `time`, `user`. Классический анти-паттерн.

Заменяем на `ActivityLog` с `GenericForeignKey` на целевой объект.

---

## Зависимости

- **Блокируется:** T-2-013 (Panel в новом месте), T-2-014 (Application в новом месте)
- **Блокирует:** T-2-023 (backfill), задача владельца #11 (единый журнал)

---

## Что нужно сделать

### Шаг 1. Модель

`apps/activity/models.py`:

```python
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class ActivityLog(models.Model):
    """Единый журнал событий по любым объектам (панель, экран, заявка, ячейка)."""
    
    class EventType(models.TextChoices):
        # Panel events
        PANEL_MOVED              = 'panel.moved',              'Панель перемещена'
        PANEL_CONDITION_CHANGED  = 'panel.condition_changed',  'Состояние панели изменено'
        PANEL_BREAKDOWN          = 'panel.breakdown',          'Поломка панели'
        PANEL_SERVICE_NOTE       = 'panel.service_note',       'Заметка сервиса о панели'
        PANEL_COMMENT_ADDED      = 'panel.comment_added',      'Комментарий к панели'
        
        # Display events
        DISPLAY_PANEL_INSTALLED  = 'display.panel_installed',  'Панель установлена'
        DISPLAY_PANEL_REMOVED    = 'display.panel_removed',    'Панель снята'
        DISPLAY_CREATED          = 'display.created',          'Экран создан'
        DISPLAY_NOTE             = 'display.note',             'Заметка об экране'
        
        # Cell events
        CELL_NOTE                = 'cell.note',                'Заметка о ячейке'
        
        # Application-related (в дополнение к ApplicationEvent — для глобальных выборок)
        APPLICATION_CREATED      = 'application.created',      'Заявка создана'
        APPLICATION_TRANSITIONED = 'application.transitioned', 'Заявка перешла в новый статус'
        
        # Monitoring reports
        MONITORING_REPORT        = 'monitoring.report',        'Отчёт мониторинга'
    
    event_type = models.CharField(
        max_length=48,
        choices=EventType.choices,
        db_index=True,
    )
    
    # Generic FK на объект, к которому относится событие
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
    )
    target_object_id = models.CharField(
        max_length=64,
        null=True, blank=True,
        db_index=True,
        help_text='строка — т.к. PK может быть и int (Cell), и name-string (Panel)',
    )
    target = GenericForeignKey('target_content_type', 'target_object_id')
    
    # Кто совершил действие (может быть system при autocreate)
    actor_username = models.CharField(
        max_length=150,
        default='system',
        db_index=True,
    )
    actor_id = models.IntegerField(null=True, blank=True)
    
    # Что произошло
    occurred_at = models.DateTimeField(db_index=True)
    description = models.CharField(
        max_length=500,
        blank=True, default='',
        help_text='Человекочитаемое описание для UI',
    )
    comment = models.TextField(
        max_length=2000,
        blank=True, default='',
    )
    file = models.FileField(
        upload_to='activity_log/%Y/%m/',
        blank=True, null=True,
    )
    
    # Дополнительные данные (id связанной сущности, предыдущее состояние и т.п.)
    payload = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'activity_log'
        verbose_name = 'Событие журнала'
        verbose_name_plural = 'Журнал событий'
        ordering = ['-occurred_at', '-id']
        indexes = [
            models.Index(fields=['target_content_type', 'target_object_id', '-occurred_at']),
            models.Index(fields=['event_type', '-occurred_at']),
            models.Index(fields=['actor_username', '-occurred_at']),
        ]
    
    def __str__(self) -> str:
        return f'{self.event_type} · {self.target} · {self.occurred_at:%Y-%m-%d %H:%M}'
```

### Шаг 2. Сервис для записи

`apps/activity/services.py`:

```python
"""Единая точка записи в ActivityLog. Все места в коде должны идти через этот сервис,
не через прямое ActivityLog.objects.create(...)."""

from __future__ import annotations
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
import structlog

from apps.activity.models import ActivityLog

logger = structlog.get_logger(__name__)


class ActivityLogger:
    """Тонкий сервис-обёртка. Внедряется в use-case'ы через DI или singleton."""
    
    def log(
        self,
        *,
        event_type: str,
        target,
        actor,
        description: str = '',
        comment: str = '',
        file=None,
        payload: dict | None = None,
        occurred_at=None,
    ) -> ActivityLog:
        ct = ContentType.objects.get_for_model(type(target)) if target else None
        
        entry = ActivityLog.objects.create(
            event_type=event_type,
            target_content_type=ct,
            target_object_id=str(target.pk) if target else None,
            actor_username=getattr(actor, 'username', str(actor)) if actor else 'system',
            actor_id=getattr(actor, 'id', None),
            occurred_at=occurred_at or timezone.now(),
            description=description or '',
            comment=comment or '',
            file=file,
            payload=payload or {},
        )
        logger.info('activity_logged',
                    event_type=event_type,
                    target=str(target),
                    actor=entry.actor_username,
                    log_id=entry.id)
        return entry


# Singleton для простоты вызовов
activity_logger = ActivityLogger()
```

### Шаг 3. Admin

`apps/activity/admin.py`:
```python
from django.contrib import admin
from .models import ActivityLog

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'occurred_at', 'event_type', 'actor_username', 'target', 'description')
    list_filter = ('event_type', 'occurred_at')
    search_fields = ('actor_username', 'comment', 'description', 'target_object_id')
    date_hierarchy = 'occurred_at'
    readonly_fields = ('target_content_type', 'target_object_id', 'target', 'occurred_at',
                       'event_type', 'actor_username', 'actor_id', 'description',
                       'comment', 'file', 'payload')
    
    def has_add_permission(self, request):
        return False  # только через сервис
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # админ может, но в проде — нет
```

### Шаг 4. Тесты

```python
def test_activity_logger_creates_entry(panels_factory, ms_user_factory):
    from apps.activity.services import activity_logger
    
    panel = panels_factory()
    user = ms_user_factory()
    
    entry = activity_logger.log(
        event_type='panel.condition_changed',
        target=panel,
        actor=user,
        description=f'Панель {panel.name} → problem',
        comment='Моргает',
        payload={'from': 'work', 'to': 'problem'},
    )
    
    assert entry.pk
    assert entry.target == panel
    assert entry.actor_username == user.username
    assert entry.actor_id == user.id
    assert entry.payload['from'] == 'work'

def test_activity_logger_with_system_actor():
    from apps.activity.services import activity_logger
    entry = activity_logger.log(
        event_type='display.created',
        target=None,
        actor=None,
        description='Display created via automation',
    )
    assert entry.actor_username == 'system'
    assert entry.actor_id is None
    assert entry.target is None
```

---

## Критерии приёмки

- [ ] Модель `ActivityLog` создана, миграция применяется
- [ ] Индексы на `(target_ct, target_id, occurred_at)` и `(event_type, occurred_at)` присутствуют
- [ ] `ActivityLogger` сервис написан, singleton `activity_logger` экспортируется
- [ ] Admin показывает журнал, запись через админку запрещена
- [ ] Unit-тесты на сервис — минимум 5 сценариев (target/actor/payload/file)
- [ ] Coverage нового кода ≥ 80%
- [ ] 5 старых History-моделей пока **остались на месте** (удаление в T-2-024)

---

## Что НЕ делать

- **НЕ удаляй** старые History-модели в этой задаче — T-2-024 после паузы
- **НЕ пиши** прямо `ActivityLog.objects.create()` — только через `activity_logger.log()`
- **НЕ добавляй** поле `target_type: CharField` вместо GenericFK — теряем типобезопасность и rich queries

---

## Риски

- **GenericFK тормозит.** `.filter(target=panel)` делает два JOIN. Для большой истории — N+1. Митигация: добавить `.prefetch_related('target')` где используется, или денормализованные поля `target_kind: str`, `target_display_id: int` для фильтров.
- **target_object_id — CharField.** Из-за того что `Panel.pk` в будущем может стать UUID. Сейчас int для application/cell, string для panel (так как `name` = PK через to_field). После T-2-025 (FK to id) — все integer, но пока оставляем char для гибкости.
- **ContentType stale.** При переименовании модели `django_content_type` может иметь дубли. После T-2-013 прогнать `python manage.py remove_stale_contenttypes`.

---

## Next step

Следующая задача — T-2-023 бекфилл данных из 5 старых History-таблиц в `ActivityLog`.
