# T-2-023. Миграция: 5 HistoryReport → `ActivityLog`

> **Тип:** migration / data
> **Приоритет:** P0
> **Оценка:** 3 часа
> **Фаза:** 2
> **Статус:** blocked

---

## Цель

Перенести исторические данные из всех пяти старых History-моделей в единый `ActivityLog`. Сохранить целостность: каждая запись — ссылается на свой `target` (Panel / Display / Application / Cell).

---

## Зависимости

- **Блокируется:** T-2-022 (ActivityLog создан)
- **Блокирует:** T-2-024 (удаление старых таблиц)

---

## Источники данных

| Таблица | Target | event_type (куда мапим) |
|---|---|---|
| `history_application` | Application (по `application_id` строковой) | `application.transitioned` |
| `history_panel` (PanelHistoryReport) | Panel (по `panel_id`) | см. ниже по `type_report` |
| `history_display` (DisplayHistoryReport) | Display (по `display_id`) | см. ниже по `type_event` |
| Возможно ещё cell-history? | Cell | `cell.note` |

Проверить точные имена таблиц и полей перед миграцией:
```bash
python manage.py inspectdb | grep -A 5 "class HistoryPanel\|class HistoryDisplay\|class HistoryApplication"
```

---

## Маппинг type → event_type

Существующие значения `type_report` / `type_event` в старых таблицах (читай текущий код):
- `'moving'` → `'panel.moved'` + дублирующий `'display.panel_installed'` или `'display.panel_removed'`
- `'condition'` → `'panel.condition_changed'`
- `'breakdown'` → `'panel.breakdown'`
- `'service'` → `'panel.service_note'`
- `'none_type'` → `'panel.comment_added'`

---

## Что нужно сделать

### Шаг 1. Management command

Не делаем data-migration через `RunPython` в этом случае — объём может быть большой. Вместо этого:

`apps/activity/management/commands/backfill_activity_log.py`:

```python
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils.timezone import make_aware
import structlog

from apps.activity.models import ActivityLog

logger = structlog.get_logger(__name__)


TYPE_REPORT_TO_EVENT = {
    'moving':    ActivityLog.EventType.PANEL_MOVED,
    'condition': ActivityLog.EventType.PANEL_CONDITION_CHANGED,
    'breakdown': ActivityLog.EventType.PANEL_BREAKDOWN,
    'service':   ActivityLog.EventType.PANEL_SERVICE_NOTE,
    'none_type': ActivityLog.EventType.PANEL_COMMENT_ADDED,
}


class Command(BaseCommand):
    help = 'Миграция данных из 5 History-таблиц → ActivityLog'
    
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--batch-size', type=int, default=1000)
        parser.add_argument('--source', choices=['panel', 'display', 'application', 'all'], default='all')
    
    def handle(self, *args, **opts):
        dry = opts['dry_run']
        bs = opts['batch_size']
        src = opts['source']
        
        # Импортируем модели из старых apps (compat-shims работают)
        from main_menu.models import PanelHistoryReport, DisplayHistoryReport
        from application.models import ApplicationHistoryReport
        from apps.directory.panels.models import Panel
        from apps.directory.displays.models import Display
        from apps.workflow.applications.models import Application
        
        ct_panel = ContentType.objects.get_for_model(Panel)
        ct_display = ContentType.objects.get_for_model(Display)
        ct_application = ContentType.objects.get_for_model(Application)
        
        if src in ('panel', 'all'):
            self._migrate(
                qs=PanelHistoryReport.objects.all(),
                build=lambda h: self._build_from_panel_history(h, ct_panel),
                batch_size=bs, dry_run=dry, label='panel_history',
            )
        
        if src in ('display', 'all'):
            self._migrate(
                qs=DisplayHistoryReport.objects.all(),
                build=lambda h: self._build_from_display_history(h, ct_display),
                batch_size=bs, dry_run=dry, label='display_history',
            )
        
        if src in ('application', 'all'):
            self._migrate(
                qs=ApplicationHistoryReport.objects.all(),
                build=lambda h: self._build_from_app_history(h, ct_application),
                batch_size=bs, dry_run=dry, label='app_history',
            )
    
    def _build_from_panel_history(self, h, ct):
        event_type = TYPE_REPORT_TO_EVENT.get(h.type_report, 'panel.comment_added')
        return ActivityLog(
            event_type=event_type,
            target_content_type=ct,
            target_object_id=h.panel.name if h.panel else None,
            actor_username=h.user or 'system',
            actor_id=None,
            occurred_at=h.time,
            description=h.description or '',
            comment=h.comment or '',
            payload={'legacy_id': h.id, 'type_report': h.type_report},
        )
    
    def _build_from_display_history(self, h, ct):
        # type_event в display-истории — другой enum
        event_type = (ActivityLog.EventType.DISPLAY_PANEL_INSTALLED
                      if h.type_event == 'moving'
                      else ActivityLog.EventType.DISPLAY_NOTE)
        return ActivityLog(
            event_type=event_type,
            target_content_type=ct,
            target_object_id=str(h.display.id) if h.display else None,
            actor_username=h.user or 'system',
            actor_id=None,
            occurred_at=h.time,
            description=h.description or '',
            comment=h.comment or '',
            payload={'legacy_id': h.id, 'type_event': h.type_event,
                     'slot_id': h.slot_id if hasattr(h, 'slot_id') else None},
        )
    
    def _build_from_app_history(self, h, ct):
        # Application history — менее структурированная, делаем единый event_type
        return ActivityLog(
            event_type=ActivityLog.EventType.APPLICATION_TRANSITIONED,
            target_content_type=ct,
            target_object_id=str(h.application_id) if h.application_id else None,
            actor_username=h.user or 'system',
            actor_id=None,
            occurred_at=h.time,
            description=h.description or '',
            comment=h.comment or '',
            payload={'legacy_id': h.id},
        )
    
    def _migrate(self, qs, build, batch_size, dry_run, label):
        total = qs.count()
        self.stdout.write(f'{label}: migrating {total} records...')
        
        batch = []
        migrated = 0
        
        for h in qs.iterator(chunk_size=batch_size):
            batch.append(build(h))
            if len(batch) >= batch_size:
                if not dry_run:
                    with transaction.atomic():
                        ActivityLog.objects.bulk_create(batch)
                migrated += len(batch)
                batch = []
                self.stdout.write(f'{label}: {migrated}/{total}')
        
        if batch:
            if not dry_run:
                with transaction.atomic():
                    ActivityLog.objects.bulk_create(batch)
            migrated += len(batch)
        
        self.stdout.write(self.style.SUCCESS(f'{label}: {migrated}/{total} DONE'))
```

### Шаг 2. Идемпотентность

Чтобы можно было запускать несколько раз без дублей:

Добавить в `ActivityLog`:
```python
legacy_source = models.CharField(max_length=64, blank=True, default='', db_index=True)
legacy_id = models.IntegerField(null=True, blank=True, db_index=True)
```

Миграция добавления этих полей — предыдущим коммитом.

В команде:
```python
# Перед build — пропускаем если уже есть
if ActivityLog.objects.filter(legacy_source=label, legacy_id=h.id).exists():
    continue
```

### Шаг 3. Верификация

Management команда `apps/activity/management/commands/verify_activity_log.py`:

```python
class Command(BaseCommand):
    def handle(self, *args, **opts):
        from main_menu.models import PanelHistoryReport, DisplayHistoryReport
        from application.models import ApplicationHistoryReport
        
        checks = [
            ('panel_history', PanelHistoryReport, ActivityLog.objects.filter(
                legacy_source='panel_history'
            )),
            ('display_history', DisplayHistoryReport, ActivityLog.objects.filter(
                legacy_source='display_history'
            )),
            ('app_history', ApplicationHistoryReport, ActivityLog.objects.filter(
                legacy_source='app_history'
            )),
        ]
        
        for label, Model, qs in checks:
            src_count = Model.objects.count()
            dst_count = qs.count()
            status = 'OK' if src_count == dst_count else 'MISMATCH'
            self.stdout.write(f'{label}: src={src_count} dst={dst_count} [{status}]')
```

### Шаг 4. Запуск

```bash
# Dry-run на dev-копии прода:
python manage.py backfill_activity_log --dry-run
# Видим количества

# Реальный запуск:
python manage.py backfill_activity_log

# Верификация:
python manage.py verify_activity_log
# Все три строки должны показать OK
```

### Шаг 5. Обновить `_build_from_panel_history` для moving

Событие `moving` у панели часто соответствует двум активностям: панель была снята с одного места И установлена на другое. Сейчас упрощаем — создаём одну запись `panel.moved`. Перед T-2-024 (удаление старых таблиц) — можно обогатить через `payload = {'from_cell_id': ..., 'to_cell_id': ...}`, если в данных это есть.

---

## Критерии приёмки

- [ ] Management command `backfill_activity_log` написан
- [ ] Идемпотентность через `legacy_source` + `legacy_id`
- [ ] Verify command подтверждает src==dst counts по всем трём источникам
- [ ] Тест на dev-копии прода: количество ActivityLog = сумме 3 source-tables
- [ ] Запускать можно с `--dry-run`, `--batch-size`, `--source`
- [ ] 5 старых таблиц **остались на месте** (для T-2-024)

---

## Что НЕ делать

- **НЕ удаляй** старые таблицы — T-2-024
- **НЕ применяй** на проде без предварительного прогона на dev-копии
- **НЕ запускай** атомарно всё одним `transaction.atomic` — при миллионе записей БД заблокируется
- **НЕ выкидывай** записи где `user` пустой — ставь `'system'`, это валидное значение

---

## Риски

- **Большой объём.** Если history суммарно >1M строк — миграция идёт часами. Выбрать ночное окно.
- **Данные «грязные».** У какой-то записи `time=NULL`, `panel` удалён, и т.п. Логировать такие как warnings и пропускать (в payload сохранять raw данные).
- **Повторный запуск.** Если упало в середине — `legacy_source+legacy_id` позволит продолжить. Проверить индекс на `(legacy_source, legacy_id)` — нужен для быстрой проверки.

---

## Follow-up

После T-2-024 (удаление старых таблиц) записи в `ActivityLog` останутся навсегда, `legacy_source` + `legacy_id` можно оставить для аудита.
