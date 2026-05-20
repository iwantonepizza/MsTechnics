# T-5-030 / T-5-031 / T-5-032 / T-5-033. Gmail-парсер VNNOX-алармов

> **Тип:** integration
> **Приоритет:** P1
> **Оценка:** 6 часов (2 + 1.5 + 1.5 + 1)
> **Фаза:** 5
> **Статус:** done
> **Взял:** GPT-5 Codex

---

## Контекст

VNNOX (поставщик светодиодов) шлёт письма на gmail-аккаунт MsTechnics при событиях с панелями: `Faulty Alarm`, `Recovery Notification`. Из них надо парсить и создавать `AlarmEvent` (но НЕ заявки автоматически — защита от шума).

Владелец прислал 4 примера писем — формат стабильный.

---

## Зависимости

- **Блокируется:** Gmail OAuth работает (он есть в legacy `mail/views.py`)
- **Блокирует:** ничего

---

## T-5-030. Gmail-parser

### Структура писем (по примерам владельца)

```
Subject: Faulty Alarm Notification: Колизей
       | Recovery Notification: Колизей

Body:
  Device：2YHA23816W3A10048571-00
  Screen Alarm Time：(UTC+05:00) 2026-04-23 00:01:28
  Screen Time Zone：UTC+05:00 ...
  Screen Address：Lenin Street, 60, Perm, ...
  Associated Email： ...
  
  New Alarms / Recovered This Time
  ─────────────────────────────────────────────
  Alarm Time           | Option              | Level   | Position                                           | Current
  2026-04-23 00:01:28  | Receiving card ...  | Faulty  | Screen(No:1)-Sending card(No:1)-Eth port(No:1)-RC(No:13) | -
  2026-04-23 00:01:28  | Receiving card ...  | Faulty  | ...-Receiving card(No:27)                          | -
  ...
```

### Парсер

`apps/integrations/gmail_alarms/parsers.py`:

```python
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AlarmType(Enum):
    FAULTY = 'faulty'
    RECOVERY = 'recovery'


@dataclass
class AlarmRecord:
    type: AlarmType
    device_id: str
    screen_name: str
    timestamp: datetime
    receiving_card_no: int  # = номер ячейки, по подтверждению владельца
    raw_position: str
    raw_email_subject: str


SUBJECT_RE = re.compile(r'^(Faulty Alarm|Recovery) Notification: (.+)$')
DEVICE_RE = re.compile(r'Device[：:]\s*([A-Z0-9-]+)')
TIME_RE = re.compile(r'Screen (?:Alarm|Recovery) Time[：:]\s*\(([^)]+)\)\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
RC_RE = re.compile(r'Receiving card\(No:(\d+)\)')


def parse_alarm_email(subject: str, body: str) -> list[AlarmRecord]:
    """Парсит одно письмо → 0+ AlarmRecord (одна на каждую receiving card)."""
    
    m = SUBJECT_RE.match(subject)
    if not m:
        return []
    
    alarm_type = AlarmType.FAULTY if m.group(1) == 'Faulty Alarm' else AlarmType.RECOVERY
    screen_name = m.group(2).strip()
    
    device_m = DEVICE_RE.search(body)
    if not device_m:
        return []
    device_id = device_m.group(1)
    
    time_m = TIME_RE.search(body)
    if not time_m:
        return []
    timestamp = datetime.strptime(time_m.group(2), '%Y-%m-%d %H:%M:%S')
    # тут можно учесть тз из time_m.group(1) если важно
    
    # Все упоминания "Receiving card(No:NN)" в теле = алармы
    rc_numbers = sorted(set(int(x) for x in RC_RE.findall(body)))
    
    return [
        AlarmRecord(
            type=alarm_type,
            device_id=device_id,
            screen_name=screen_name,
            timestamp=timestamp,
            receiving_card_no=rc,
            raw_position=f'RC(No:{rc})',
            raw_email_subject=subject,
        )
        for rc in rc_numbers
    ]
```

### Цикл получения

`apps/integrations/gmail_alarms/management/commands/pull_alarms.py`:

```python
from django.core.management.base import BaseCommand
from apps.integrations.gmail_alarms.services import gmail_pull_unread, process_alarm_record


class Command(BaseCommand):
    help = 'Pull unread emails from VNNOX, parse, create AlarmEvent'
    
    def handle(self, *args, **opts):
        # Use existing Gmail OAuth from legacy mail/ for auth — но новый код в integrations/
        for msg in gmail_pull_unread(query='from:service@alimail.vnnox.com is:unread'):
            records = parse_alarm_email(msg['subject'], msg['body'])
            for r in records:
                process_alarm_record(r)
            mark_as_read(msg['id'])
```

Запуск через cron каждые 5 минут.

### Критерии T-5-030

- [ ] Парсер handle Faulty + Recovery
- [ ] 4 примера владельца дают правильные `receiving_card_no` (тесты с фикстурами)
- [ ] Management command подключается к Gmail и pull'ит unread
- [ ] Email после обработки помечается as read

---

## T-5-031. AlarmEvent модель + связь с Display

`apps/integrations/gmail_alarms/models.py`:

```python
class AlarmEvent(models.Model):
    """Аларм или recovery от VNNOX."""
    
    class Type(TextChoices):
        FAULTY = 'faulty', 'Аварийное'
        RECOVERY = 'recovery', 'Восстановление'
    
    type = CharField(max_length=10, choices=Type.choices, db_index=True)
    
    # Связи
    display = ForeignKey('directory_displays.Display', on_delete=PROTECT, null=True, blank=True,
                         related_name='alarms')  # null если device_id не сматчился
    cell = ForeignKey('directory_displays.Cell', on_delete=SET_NULL, null=True, blank=True)
    panel = ForeignKey('directory_panels.Panel', on_delete=SET_NULL, null=True, blank=True)
    
    # Сырые данные (для аудита/отладки)
    device_id = CharField(max_length=64, db_index=True)
    screen_name_raw = CharField(max_length=200)
    receiving_card_no = IntegerField()
    raw_position = CharField(max_length=200, blank=True)
    raw_email_subject = CharField(max_length=300, blank=True)
    
    # Когда событие
    occurred_at = DateTimeField(db_index=True)
    received_at = DateTimeField(auto_now_add=True)
    
    # Resolved?
    resolved_at = DateTimeField(null=True, blank=True, db_index=True,
                                help_text='Recovery перешло в resolved')
    resolved_by_alarm = OneToOneField('self', null=True, blank=True, on_delete=SET_NULL,
                                       related_name='resolves')
    
    class Meta:
        db_table = 'alarm_event'
        indexes = [
            models.Index(fields=['device_id', 'receiving_card_no', '-occurred_at']),
            models.Index(fields=['display', 'resolved_at', '-occurred_at']),
        ]
```

### `Display.vnnox_device_id`

Добавить поле:
```python
class Display(models.Model):
    # ...
    vnnox_device_id = CharField(max_length=64, blank=True, default='', db_index=True,
                                  help_text='Серийник VNNOX, для маппинга алармов')
```

Миграция + админка для админа: вписать `vnnox_device_id` в каждом экране.

### Маппинг

```python
# apps/integrations/gmail_alarms/services.py
def process_alarm_record(record: AlarmRecord):
    from apps.directory.displays.models import Display, Cell
    from apps.directory.panels.models import Panel
    
    # 1. Найти Display по device_id
    display = Display.objects.filter(vnnox_device_id=record.device_id).first()
    
    # 2. Найти Cell на этом display с position == receiving_card_no
    # (владелец подтвердил: receiving card = ячейка)
    cell = None
    panel = None
    if display:
        cell = Cell.objects.filter(display=display, position=str(record.receiving_card_no)).first()
        if cell:
            panel = cell.panel
    
    # 3. Если recovery — попытаться сопоставить с открытым faulty
    resolved_by = None
    if record.type == AlarmType.RECOVERY and display:
        resolved_by = AlarmEvent.objects.filter(
            display=display,
            receiving_card_no=record.receiving_card_no,
            type=AlarmEvent.Type.FAULTY,
            resolved_at__isnull=True,
        ).order_by('-occurred_at').first()
    
    # 4. Создать AlarmEvent
    event = AlarmEvent.objects.create(
        type=record.type.value,
        display=display,
        cell=cell,
        panel=panel,
        device_id=record.device_id,
        screen_name_raw=record.screen_name,
        receiving_card_no=record.receiving_card_no,
        raw_position=record.raw_position,
        raw_email_subject=record.raw_email_subject,
        occurred_at=record.timestamp,
    )
    
    # 5. Если это recovery — закрыть открытый faulty
    if resolved_by:
        from django.utils import timezone
        resolved_by.resolved_at = timezone.now()
        resolved_by.resolved_by_alarm = event
        resolved_by.save(update_fields=['resolved_at', 'resolved_by_alarm'])
    
    return event
```

### Критерии T-5-031

- [ ] AlarmEvent создаётся
- [ ] Маппинг `device_id` → Display работает
- [ ] Recovery закрывает открытый Faulty
- [ ] Admin для AlarmEvent с фильтрами по resolved/display

---

## T-5-032. UI на Display View — лента VNNOX-алармов

Расширение `DisplayViewPage` (T-4-013) — отдельная вкладка/панель «Алармы VNNOX».

### API

```
GET /api/v1/displays/{slug}/alarms?resolved=false&limit=50
```

Список открытых алармов на этом экране. Реализуется отдельным action или просто в `apps/interface/api/v1/alarms/`.

### Frontend

В `DisplayViewPage` — добавить tab `Alarms` рядом с `Applications`. Внутри — таблица:

```
| Time     | Cell | Status   | Action            |
|----------|------|----------|-------------------|
| 14:30    | 13   | 🔴 Open  | [Создать заявку]  |
| 14:25    | 27   | 🟢 Closed (auto recovery) |    |
```

Кнопка «Создать заявку» — pre-fills form с position='13', comment='VNNOX: Receiving card 13 abnormal'.

### Критерии T-5-032

- [ ] API endpoint работает
- [ ] Tab появляется в DisplayView
- [ ] Open-state красный, closed — зелёный
- [ ] Кнопка → CreateApplicationModal с pre-fill

---

## T-5-033. Уведомление мониторщику

Если аларм висит > N минут (default: 15 минут) и нет recovery — уведомление мониторщику.

### Implementation

Добавить cron-команду:

```python
# apps/integrations/gmail_alarms/management/commands/check_unresolved_alarms.py

THRESHOLD_MINUTES = 15

def handle(self, *args, **opts):
    threshold_time = timezone.now() - timedelta(minutes=THRESHOLD_MINUTES)
    
    unresolved = AlarmEvent.objects.filter(
        type='faulty',
        resolved_at__isnull=True,
        occurred_at__lt=threshold_time,
        display__isnull=False,
    )
    
    for alarm in unresolved:
        # Idempotency: если уже уведомили — skip
        already = Notification.objects.filter(
            related_target_ct__model='alarmevent',
            related_target_id=str(alarm.id),
        ).exists()
        if already:
            continue
        
        # Уведомить мониторщиков города
        recipients = MsUser.objects.filter(
            permission__in=['monitoring', 'admin', 'all'],
            allowed_city=alarm.display.city,
        ).distinct()
        
        for user in recipients:
            template = NotificationTemplate.objects.get(name='vnnox_alarm_unresolved')
            notif = Notification.objects.create(
                template=template,
                recipient=user,
                rendered_text=template.text.format(
                    display=alarm.display.description,
                    cell=alarm.receiving_card_no,
                    minutes=int((timezone.now() - alarm.occurred_at).total_seconds() / 60),
                ),
                related_target=alarm,
            )
            notification_dispatcher.dispatch(notif)
```

В migration добавить шаблон `vnnox_alarm_unresolved`.

Cron:
```cron
*/5 * * * * cd /opt/mstechnics && python manage.py check_unresolved_alarms
```

### Критерии T-5-033

- [ ] Команда работает
- [ ] Idempotency: 1 уведомление на 1 аларм за всё его время
- [ ] Threshold 15 минут (настраивается через env)
- [ ] Уведомление приходит мониторщикам в TG/MAX

---

## Финальный чек

- [ ] 4 примера владельца → парсятся правильно (тестовые fixture'ы)
- [ ] Поле `Display.vnnox_device_id` — заполнено для каждого экрана (через admin)
- [ ] Алармы видны в UI Display View
- [ ] Уведомления о висящих алармах приходят
- [ ] Recovery закрывает Faulty автоматически
- [ ] Админ может вручную создать заявку из аларма

---

## Что НЕ делать

- НЕ создавать заявки автоматически из алармов — слишком много шума
- НЕ удалять обработанные письма — оставлять как 'read'
- НЕ полагаться на парсер — структура VNNOX-писем может измениться, нужны мониторинг и тесты на новых примерах
