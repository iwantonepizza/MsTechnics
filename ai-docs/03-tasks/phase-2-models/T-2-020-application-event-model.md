# T-2-020. Создать `ApplicationEvent` + миграция 28 полей

> **Тип:** migration / data
> **Приоритет:** P0 (ключ Фазы 2)
> **Оценка:** 3 часа
> **Фаза:** 2
> **Статус:** done

---

## Цель

Денормализовать 28 полей заявки (`comment_monitoring`, `time_monitoring`, `user_monitoring`, `file_monitoring` × 7 этапов) в нормализованную таблицу событий `ApplicationEvent`. Каждое событие = одна строка.

После этого рефакторинга:
- Добавление нового этапа = одно событие, не 4 колонки
- История заявки = select из одной таблицы, сортировка по времени
- API `/applications/<id>/events` — тривиален

---

## Зависимости

- **Блокируется:** T-2-003 (regression), T-2-014 (workflow structure)
- **Блокирует:** T-2-021 (удаление старых полей), задача владельца #3 (кнопка истории заявки)

---

## Что нужно сделать

### Шаг 1. Модель

`apps/workflow/applications/models.py` — добавить:

```python
class ApplicationEvent(models.Model):
    """Событие жизненного цикла заявки.
    
    Заменяет 28 денормализованных полей (comment_*, time_*, user_*, file_*).
    """
    
    class EventType(models.TextChoices):
        CREATED            = 'created',            'Создана'
        CONTROL_APPLIED    = 'control_applied',    'Принята в контроле'
        SENT_TO_SERVICE    = 'sent_to_service',    'Отправлена в сервис'
        SERVICE_APPLIED    = 'service_applied',    'Принята в сервисе'
        WORK_COMPLETED     = 'work_completed',     'Ремонт выполнен'
        WORK_UNABLE        = 'work_unable',        'Ремонт невозможен'
        ARCHIVED           = 'archived',           'Архивирована'
        # Дополнительно для полноты:
        COMMENT_ADDED      = 'comment_added',      'Комментарий добавлен'
        EXECUTOR_CHANGED   = 'executor_changed',   'Исполнитель изменён'
    
    application = models.ForeignKey(
        'workflow_applications.Application',
        on_delete=models.CASCADE,
        related_name='events',
    )
    event_type = models.CharField(
        max_length=32,
        choices=EventType.choices,
        db_index=True,
    )
    actor_username = models.CharField(
        max_length=150,
        verbose_name='Кто совершил',
        help_text='Username на момент события (для истории даже если юзер удалён)',
    )
    actor_id = models.IntegerField(
        null=True, blank=True,
        help_text='ID юзера, может быть NULL если юзер удалён или action был системный',
    )
    
    occurred_at = models.DateTimeField(
        verbose_name='Время события',
        db_index=True,
    )
    
    comment = models.TextField(
        max_length=2000,
        blank=True, default='',
        verbose_name='Комментарий',
    )
    file = models.FileField(
        upload_to='application_events/%Y/%m/',
        blank=True, null=True,
        verbose_name='Прикреплённый файл',
    )
    
    # FSM tracking
    state_from = models.CharField(max_length=40, blank=True, default='')
    state_to   = models.CharField(max_length=40, blank=True, default='')
    
    # Дополнительная структурированная инфа (executor_id, device_id и т.п.)
    payload = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'application_event'
        verbose_name = 'Событие заявки'
        verbose_name_plural = 'События заявок'
        ordering = ['application', 'occurred_at', 'id']
        indexes = [
            models.Index(fields=['application', 'occurred_at']),
            models.Index(fields=['event_type', 'occurred_at']),
        ]
    
    def __str__(self) -> str:
        return f'{self.application_id} · {self.event_type} · {self.occurred_at:%Y-%m-%d %H:%M}'
```

### Шаг 2. Миграция — `CreateModel` (обычная)

```bash
python manage.py makemigrations workflow_applications --name=create_application_event
```

Эта миграция создаёт таблицу физически.

### Шаг 3. Data-migration — backfill из старых полей

```bash
python manage.py makemigrations workflow_applications --empty --name=backfill_application_events
```

Содержимое:

```python
from django.db import migrations
from django.db.models import Q


def forwards(apps, schema_editor):
    Application = apps.get_model('workflow_applications', 'Application')
    Event = apps.get_model('workflow_applications', 'ApplicationEvent')
    
    # Маппинг: stage_suffix → event_type
    STAGE_TO_EVENT = [
        # (stage suffix in field names, event_type, state_from, state_to)
        ('monitoring',        'created',            '',                  'sent_to_control'),
        ('control_apply',     'control_applied',    'sent_to_control',   'apply_in_control'),
        ('control_send',      'sent_to_service',    'apply_in_control',  'sent_to_service'),
        ('service_apply',     'service_applied',    'sent_to_service',   'work_in_service'),
        ('control_at_work',   'work_completed',     'work_in_service',   'done'),
        ('control_unable',    'work_unable',        'work_in_service',   'unable'),
        ('control_archive',   'archived',           '',                  ''),   # из done/unable
    ]
    
    events_to_create = []
    skipped = 0
    
    # iterator chunk — для больших таблиц
    for app in Application.objects.all().iterator(chunk_size=500):
        for suffix, event_type, state_from, state_to in STAGE_TO_EVENT:
            time_val  = getattr(app, f'time_{suffix}',    None)
            if not time_val:
                continue  # этот этап не проходился
            
            comment   = getattr(app, f'comment_{suffix}', '') or ''
            user      = getattr(app, f'user_{suffix}',    '') or 'system'
            file_val  = getattr(app, f'file_{suffix}',    None)
            
            # Special case: archived → state_from выводим из статуса заявки
            if event_type == 'archived':
                # если сейчас в archive_done — шло от done; если archive_unable — от unable
                current_status_name = app.status.name if app.status else ''
                if current_status_name == 'archive_done':
                    sf, st = 'done', 'archive_done'
                elif current_status_name == 'archive_unable':
                    sf, st = 'unable', 'archive_unable'
                else:
                    sf, st = '', ''
            else:
                sf, st = state_from, state_to
            
            events_to_create.append(Event(
                application=app,
                event_type=event_type,
                actor_username=user,
                actor_id=None,   # исторически не знаем ID
                occurred_at=time_val,
                comment=comment,
                file=file_val if file_val else None,
                state_from=sf,
                state_to=st,
                payload={},
            ))
        
        # flush каждые 1000 событий
        if len(events_to_create) >= 1000:
            Event.objects.bulk_create(events_to_create, ignore_conflicts=False)
            events_to_create = []
    
    if events_to_create:
        Event.objects.bulk_create(events_to_create, ignore_conflicts=False)


def reverse(apps, schema_editor):
    Event = apps.get_model('workflow_applications', 'ApplicationEvent')
    Event.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('workflow_applications', 'XXXX_create_application_event'),
    ]
    atomic = False  # для больших БД — не одна транзакция
    operations = [
        migrations.RunPython(forwards, reverse),
    ]
```

### Шаг 4. Свойства-ярлыки на Application (совместимость)

Чтобы старые views не падали, добавить computed properties:

```python
class Application(models.Model):
    # ... поля как были ...
    
    @property
    def comment_monitoring_new(self):
        """Новая версия через ApplicationEvent (для постепенного перехода)."""
        ev = self.events.filter(event_type='created').first()
        return ev.comment if ev else ''
    
    # И так далее для других (если нужно в шаблонах).
    # Но ЛУЧШЕ обновить шаблоны сразу на новую модель.
```

**Альтернативно — метод:**
```python
def get_event(self, event_type: str):
    return self.events.filter(event_type=event_type).first()
```

В шаблонах:
```django
{{ application.get_event.comment }}  {# not ideal но работает #}
```

Но в Фазе 4 всё уйдёт в API — шаблоны временно уродуем, важно что данные не потеряны.

### Шаг 5. Тесты

```python
def test_application_event_backfill_creates_events(application_factory, ...):
    app = application_factory(
        status__name='done',
        time_monitoring=timezone.now() - timedelta(days=2),
        comment_monitoring='Первый комментарий',
        user_monitoring='monitor_user',
        time_control_apply=timezone.now() - timedelta(days=1),
        comment_control_apply='Принял',
        user_control_apply='control_user',
    )
    # Apply миграции вручную в тесте — или запускаем её и смотрим результат
    # Проще: пишем data-migration как management command и тестируем её отдельно
```

### Шаг 6. Management command для верификации

`apps/workflow/applications/management/commands/verify_application_events.py`:

```python
from django.core.management.base import BaseCommand
from apps.workflow.applications.models import Application

class Command(BaseCommand):
    help = 'Проверяет что для каждой заявки есть соответствующие ApplicationEvent'
    
    def handle(self, *args, **opts):
        bad = 0
        for app in Application.objects.all().iterator(chunk_size=500):
            # у заявки с time_monitoring должно быть событие created
            if app.time_monitoring and not app.events.filter(event_type='created').exists():
                self.stdout.write(f'BAD #{app.id}: no created event')
                bad += 1
        
        total = Application.objects.count()
        self.stdout.write(f'Checked {total}, bad {bad}')
```

---

## Критерии приёмки

- [ ] Модель `ApplicationEvent` создана
- [ ] Миграция таблицы применяется на чистой БД
- [ ] Data-миграция на копии прода успешно мигрирует всё
- [ ] `python manage.py verify_application_events` — 0 bad
- [ ] Regression-тесты T-2-003 — проходят
- [ ] Unit-тесты на модель и миграцию (минимум 5)
- [ ] Admin настроен — `ApplicationEventAdmin` с list_display
- [ ] 28 старых полей на `Application` **ОСТАЛИСЬ** — удалять только в T-2-021 после паузы

---

## Что НЕ делать

- **НЕ удаляй** 28 старых полей в этой задаче — T-2-021 после 2-недельной паузы
- **НЕ рефактори** views которые пишут в старые поля (сервис Фазы 2 T-2-040 заменит их)
- **НЕ делай атомарную миграцию для backfill** — падение в середине = катастрофа
- **НЕ копируй** backfill-код в тесты — тестируй через `call_command`

---

## Верификация руками

После миграции на dev:

```sql
-- У большинства заявок должно быть 1-5 событий
SELECT count(*), application_id FROM application_event GROUP BY application_id 
ORDER BY count(*) DESC LIMIT 10;

-- Проверить сохранность комментариев:
SELECT a.id, a.comment_monitoring, e.comment 
FROM application a LEFT JOIN application_event e 
ON e.application_id = a.id AND e.event_type = 'created'
WHERE a.comment_monitoring IS NOT NULL AND a.comment_monitoring != ''
LIMIT 20;
-- Ожидание: a.comment_monitoring == e.comment
```

---

## Вопросы

- [ ] Что делать с заявками, у которых `time_control_apply` есть, а `time_monitoring` нет? (скорее всего, баги в legacy — фиксируем как created с `occurred_at = time_control_apply - 1min`)
- [ ] Нужны ли event'ы для comment-only обновлений (когда юзер добавил фото или комментарий уже после transition)? — Пока нет, можем добавить в будущем через `COMMENT_ADDED`.
