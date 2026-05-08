# Notifications — редизайн

## Implementation snapshot - 2026-05-05

- `apps.notifications` registered in `INSTALLED_APPS`.
- Added persistence layer: `NotificationTemplate`, `Notification`, `NotificationDeliveryAttempt`.
- Added channel abstraction: `BaseChannel`, `TelegramChannel` stub, `MaxChannel` stub, `EmailChannel` stub.
- Added `NotificationDispatcher` with fallback order `telegram -> max -> email`.
- Dispatcher writes one `NotificationDeliveryAttempt` per real delivery attempt, skips channels that cannot deliver, marks notification `sent` or `failed`.
- Telegram/MAX/email channels are wired for Phase 5 delivery.
- Legacy `sender_tg_message.py` and `tg_sender` were removed after T-5-011 unblock.
- `sorting_message.py` remains only as a compatibility shim for legacy imports and dispatches through `NotificationDispatcher` instead of Redis pubsub.

## Что есть сейчас

```
view → async_to_sync(presend_filters) → Redis pubsub → sender_tg_message.py → Telegram Bot API
```

**Проблемы:**

| # | Что | Почему плохо |
|---|---|---|
| 1 | Pubsub, а не очередь | Сообщение потеряно если `sender_tg_message.py` упал |
| 2 | `async_to_sync` в views | Блокирует response на время фильтрации получателей |
| 3 | Права жёстко захардкожены в `sorting_message.py` | `if application.status == "sent_to_service" and user.permission in ["service", "all"]` — нет связи с моделью |
| 4 | Нет retry при ошибке Telegram API | Bad Gateway / Rate limit → сообщение теряется |
| 5 | Нет DLQ | Что делать с «умершими» сообщениями — непонятно |
| 6 | Нет дедупликации | Одно событие может сгенерить 10 одинаковых сообщений |
| 7 | Только Telegram | А РФ блочит Telegram |
| 8 | Логи пишутся в файл + `print()` | structlog нужен |
| 9 | Нет metrics / healthcheck | Не знаем что бот «тихо умер» |

---

## Целевая архитектура

```
 Событие (app.created, app.transition, panel.condition_changed, ...)
    │
    │ emit через NotificationService
    ▼
┌───────────────────────────────────────┐
│  NotificationDispatcher               │
│  ───────────────────────────────────  │
│  1. Определить получателей            │
│     (NotificationRule + user role +   │
│      allowed_cities)                  │
│  2. Дедупликация (Redis SETEX на 60s) │
│  3. Render per channel                │
│  4. Enqueue в Redis Stream            │
└────────┬──────────────────────────────┘
         │
         ▼ Redis Stream: notifications
         │
   ┌─────┴─────────┬──────────────┐
   ▼               ▼              ▼
TelegramConsumer  MaxConsumer  EmailConsumer
 └─> TG via       └─> MAX API  └─> SMTP
     SOCKS5 proxy
     + retry + DLQ
```

---

## Ключевые классы

### `NotificationEvent` (domain)
```python
@dataclass(frozen=True)
class NotificationEvent:
    event_type: str          # "application.created" | "application.transition" | ...
    payload: dict            # snapshot of relevant data (id, status, display_slug, ...)
    created_at: datetime
```

### `NotificationRule`
```python
@dataclass(frozen=True)
class NotificationRule:
    event_type: str
    recipient_filter: Callable[[User, NotificationEvent], bool]
    template: str            # путь к шаблону рендера
    channels: list[str]      # ["telegram", "max", "email"]
    dedup_key: Callable[[NotificationEvent], str] | None
```

Правила регистрируются в настройках или через БД (таблица `NotificationRule`).

### `NotificationService`
```python
class NotificationService:
    def __init__(self, dispatcher: Dispatcher, user_repo: UserRepository, ...):
        ...

    def emit(self, event: NotificationEvent) -> None:
        rules = self._rules_for(event.event_type)
        for rule in rules:
            recipients = self._recipients_for(rule, event)
            for user in recipients:
                for channel in rule.channels:
                    msg = self._render(rule.template, user, event)
                    if self._is_duplicate(user, rule, event):
                        continue
                    self._dispatcher.enqueue(
                        channel=channel, user_id=user.id, message=msg, event=event
                    )
```

### `Dispatcher`
```python
class RedisStreamDispatcher:
    def enqueue(self, channel: str, user_id: int, message: str, event: NotificationEvent) -> None:
        self._redis.xadd(
            name=f"notifications.{channel}",
            fields={"user_id": user_id, "message": message, "event_type": event.event_type, "event_id": event.id},
        )
```

### `NotificationConsumer` (per channel)
```python
class TelegramConsumer:
    STREAM = "notifications.telegram"
    GROUP = "tg-workers"
    MAX_RETRIES = 5

    def run(self) -> None:
        while True:
            msgs = self._redis.xreadgroup(self.GROUP, "worker-1", {self.STREAM: ">"}, count=10, block=5000)
            for msg in msgs:
                try:
                    self._deliver(msg)
                    self._redis.xack(self.STREAM, self.GROUP, msg.id)
                except Exception:
                    self._retry_or_dlq(msg)
```

### `NotificationChannel` (абстракция)
```python
class NotificationChannel(Protocol):
    def can_deliver(self, user: MsUser) -> bool: ...
    def deliver(self, user: MsUser, message: str) -> DeliveryResult: ...

class TelegramChannel: ...
class MaxChannel: ...
class EmailChannel: ...
```

Каждый канал реализует Protocol. Регистрация в settings:

```python
NOTIFICATION_CHANNELS = {
    "telegram": "apps.notifications.channels.telegram.TelegramChannel",
    "max": "apps.notifications.channels.max.MaxChannel",
    "email": "apps.notifications.channels.email.EmailChannel",
}
```

---

## Fallback логика

1. Если канал `can_deliver == False` — пропускаем, шлём в следующий
2. Если все каналы упали N раз → DLQ
3. Per-user настройка «Основной канал: MAX, резерв: TG» (поле `MsUser.preferred_channels: list[str]`)

---

## Дедупликация

```python
def _dedup_key(rule, event, user):
    return f"dedup:{user.id}:{rule.event_type}:{event.payload.get('target_id')}"

# При отправке:
if redis.set(key, "1", nx=True, ex=60):
    send()
# иначе — пропускаем
```

60 секунд по дефолту, настраивается через `rule.dedup_ttl`.

---

## Healthcheck

`NotificationHealthChecker` — отдельный процесс:

1. Раз в 5 минут шлёт тестовое сообщение в специальный чат/топик `healthcheck_<channel>`
2. Если 3 раза подряд упало → sentry.capture_message + метрика
3. На `/api/v1/health/notifications` — статус всех каналов

---

## Templates

Шаблоны рендеринга — Jinja-подобные строки в БД или файлах:

```
notifications/templates/
  application_created.telegram.txt
  application_created.max.txt
  application_created.email.html
```

Пример:
```
🆕 Новая заявка #{{ application.id }}
Экран: {{ application.display.description }}
Слот: {{ application.cell.position }}
Комментарий: {{ application.comment_monitoring }}
Открыть: {{ base_url }}/control/{{ display.city.slug }}/{{ display.slug }}?app_id={{ application.id }}
```

---

## Роли и правила

Старая логика в `sorting_message.py` переписывается в `NotificationRule` записи (в БД для редактирования в админке):

| Event type | Recipients (правило) | Channels |
|---|---|---|
| `application.created` | `user.permission in ['control', 'all'] AND display.city in user.allowed_cities` | all available |
| `application.transition → sent_to_service` | `user.permission in ['service', 'all'] AND display.city in user.allowed_cities` | all |
| `application.transition → done/unable` | `user.permission in ['control', 'all']` | all |
| `panel.condition_changed (to problem)` | mirrors `application.created` | all |
| `daily_task.reminder` | assigned user only | all |

---

## Миграция с pubsub на Streams

- **Этап 1 (Фаза 1):** добавить structlog + healthcheck + retry на текущий pubsub
- **Этап 2 (Фаза 5):** параллельно написать Streams-dispatcher, гонять оба рядом неделю
- **Этап 3:** выключить pubsub, оставить Streams

---

## Telegram в РФ — workaround

См. отдельный `telegram-russia-workaround.md`. Кратко:
- SOCKS5 или HTTPS-прокси через зарубежный VPS
- `python-telegram-bot` поддерживает `proxy_url` в `Bot(...)`
- Мониторинг доступности прокси отдельным healthcheck

---

## Метрики

```
notifications_enqueued_total{event_type, channel}
notifications_delivered_total{channel}
notifications_failed_total{channel, reason}
notifications_dedup_skipped_total{event_type}
notifications_latency_seconds{channel} (histogram)
```

Экспортер Prometheus — опционально; минимум — пишем structlog и смотрим в Kibana/Grafana Loki, если они есть.

---

## Тесты

- Unit: `NotificationService.emit` с mock-dispatcher — проверка правил фильтрации
- Integration: fake Redis + fake Channels — проверка flow
- E2E: реальный TG-бот в test-chat, проверка что сообщение дошло
