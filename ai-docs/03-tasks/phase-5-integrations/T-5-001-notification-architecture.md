# T-5-001. apps/notifications/ — channels + dispatcher

> **Тип:** core / architecture
> **Приоритет:** P0
> **Оценка:** 3 часа
> **Фаза:** 5
> **Статус:** review
> **Взял:** GPT-5 Codex

---

## Цель

Спроектировать **расширяемую систему уведомлений** с подключаемыми каналами доставки и единым диспетчером.

---

## Зависимости

- **Блокируется:** ничего
- **Блокирует:** все T-5-XXX

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│ Trigger                                                      │
│  - сигнал post_save / post_transition                        │
│  - cron-задача (daily SLA check)                             │
└────────────┬─────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ NotificationDispatcher                                       │
│  - принимает Notification(recipient, template, context)      │
│  - выбирает channel(s) по правилу:                          │
│    1. Try TG (primary)                                       │
│    2. Если no delivery 30s → try MAX                        │
│    3. Если MAX тоже fail → email                            │
│  - пишет в NotificationLog                                   │
└────────────┬─────────────────────────────────────────────────┘
             │
       ┌─────┴─────┬─────────┐
       ▼           ▼         ▼
   TG Channel  MAX Chan  Email Chan
       │           │         │
       ▼           ▼         ▼
   Telegram     MAX API   SMTP
```

---

## Что сделать

### Шаг 1. Структура директорий

```
apps/notifications/
├── __init__.py
├── apps.py
├── models.py            # Notification, NotificationLog, NotificationTemplate
├── services.py          # NotificationDispatcher
├── channels/
│   ├── __init__.py
│   ├── base.py          # BaseChannel ABC
│   ├── telegram.py      # T-5-002
│   ├── max.py           # T-5-003
│   └── email.py         # T-5-004
├── triggers/
│   ├── __init__.py
│   ├── application.py   # T-5-006
│   ├── departure.py     # T-5-006
│   └── daily.py         # T-5-006
├── templates/           # NotificationTemplate seeds
└── tests/
```

### Шаг 2. Модели

```python
# apps/notifications/models.py
class NotificationTemplate(models.Model):
    """Шаблон уведомления — название + jinja2-like text."""
    name = CharField(max_length=64, unique=True, db_index=True)
    description = CharField(max_length=200, blank=True)
    text = TextField(help_text='Текст с {plaкеholders} из context')
    
    class Meta:
        db_table = 'notification_template'

class Notification(models.Model):
    """Запланированная уведомляющая отправка."""
    
    class Status(TextChoices):
        PENDING = 'pending', 'В очереди'
        SENT    = 'sent', 'Отправлено'
        FAILED  = 'failed', 'Ошибка'
        SKIPPED = 'skipped', 'Пропущено'
    
    template = ForeignKey(NotificationTemplate, on_delete=PROTECT)
    recipient = ForeignKey('user.MsUser', on_delete=CASCADE, related_name='notifications')
    
    # Что отрендерилось (для аудита):
    rendered_text = TextField(blank=True)
    context = JSONField(default=dict, blank=True)
    
    # Where this came from:
    related_target_ct = ForeignKey(ContentType, null=True, blank=True, on_delete=SET_NULL)
    related_target_id = CharField(max_length=64, null=True, blank=True)
    related_target = GenericForeignKey('related_target_ct', 'related_target_id')
    
    # Доставка:
    status = CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    primary_channel = CharField(max_length=16, blank=True)
    delivered_via = CharField(max_length=16, blank=True)  # 'telegram'|'max'|'email'
    
    created_at = DateTimeField(auto_now_add=True, db_index=True)
    sent_at = DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'notification'
        indexes = [
            models.Index(fields=['recipient', 'status', '-created_at']),
        ]
        ordering = ['-created_at']

class NotificationDeliveryAttempt(models.Model):
    """История попыток доставки одного notification."""
    notification = ForeignKey(Notification, on_delete=CASCADE, related_name='attempts')
    channel = CharField(max_length=16)
    attempted_at = DateTimeField(auto_now_add=True)
    succeeded = BooleanField()
    error_message = TextField(blank=True)
    response_payload = JSONField(default=dict, blank=True)  # webhook id, message_id, etc.
```

### Шаг 3. BaseChannel

```python
# apps/notifications/channels/base.py
from abc import ABC, abstractmethod
from typing import TypedDict

class DeliveryResult(TypedDict):
    succeeded: bool
    error: str | None
    response: dict


class BaseChannel(ABC):
    """Абстрактный канал доставки."""
    
    name: str  # 'telegram' | 'max' | 'email'
    
    @abstractmethod
    def can_deliver(self, recipient) -> bool:
        """Есть ли у получателя нужный binding (telegram_id, max_chat_id, email)."""
        ...
    
    @abstractmethod
    def deliver(self, recipient, text: str, *, context: dict = None) -> DeliveryResult:
        """Отправить уведомление. Возвращает {succeeded, error, response}."""
        ...
```

### Шаг 4. NotificationDispatcher

```python
# apps/notifications/services.py
import structlog
from typing import Iterable
from django.utils import timezone

from .channels import telegram, max, email
from .models import Notification, NotificationDeliveryAttempt

logger = structlog.get_logger(__name__)


class NotificationDispatcher:
    """Принимает Notification, пробует доставку по очереди channels."""
    
    # Порядок попыток: TG → MAX → Email
    DEFAULT_FALLBACK_ORDER = ('telegram', 'max', 'email')
    
    def __init__(self, channels: Iterable[BaseChannel] = None):
        self.channels = {c.name: c for c in (channels or [
            telegram.TelegramChannel(),
            max.MaxChannel(),
            email.EmailChannel(),
        ])}
    
    def dispatch(self, notification: Notification, fallback_order: tuple[str] = None):
        order = fallback_order or self.DEFAULT_FALLBACK_ORDER
        
        for channel_name in order:
            channel = self.channels.get(channel_name)
            if not channel or not channel.can_deliver(notification.recipient):
                continue
            
            result = channel.deliver(
                notification.recipient,
                notification.rendered_text,
                context=notification.context,
            )
            
            NotificationDeliveryAttempt.objects.create(
                notification=notification,
                channel=channel_name,
                succeeded=result['succeeded'],
                error_message=result.get('error') or '',
                response_payload=result.get('response') or {},
            )
            
            if result['succeeded']:
                notification.status = Notification.Status.SENT
                notification.delivered_via = channel_name
                notification.sent_at = timezone.now()
                notification.save(update_fields=['status', 'delivered_via', 'sent_at'])
                logger.info('notification_delivered', notification_id=notification.id, channel=channel_name)
                return True
            else:
                logger.warning('notification_delivery_failed',
                               notification_id=notification.id,
                               channel=channel_name,
                               error=result.get('error'))
        
        # Все каналы провалились
        notification.status = Notification.Status.FAILED
        notification.save(update_fields=['status'])
        logger.error('notification_all_channels_failed', notification_id=notification.id)
        return False


notification_dispatcher = NotificationDispatcher()
```

### Шаг 5. Tests

```python
# apps/notifications/tests/test_dispatcher.py
class TestNotificationDispatcher:
    def test_fallback_to_max_when_telegram_fails(self, ms_user_factory, notification_factory):
        # mock TG returns failure, MAX returns success
        # verify NotificationDeliveryAttempt has 2 records
        # notification.delivered_via == 'max'
        ...
    
    def test_skip_channel_when_can_deliver_false(self, ms_user_factory, notification_factory):
        # user без telegram_id → telegram channel skip'ит
        ...
    
    def test_all_channels_fail_marks_notification_failed(self, ...):
        ...
```

---

## Критерии приёмки

- [ ] `apps/notifications/` зарегистрирован в `INSTALLED_APPS`
- [ ] Миграция создана для 3 моделей
- [ ] `BaseChannel` ABC + 3 stub-channels (без реальной отправки в этой задаче)
- [ ] `NotificationDispatcher` с fallback order
- [ ] `NotificationDeliveryAttempt` пишется на каждую попытку
- [ ] Минимум 5 тестов dispatcher (success, fallback, no recipient, all fail, skip)

---

## Что НЕ делать

- НЕ реализовывать channels полностью — это T-5-002/003/004
- НЕ строить retry с exponential backoff в этой задаче — отдельный worker через django-q2 в T-5-040
- НЕ переписывать `sender_tg_message.py` — это T-5-011
