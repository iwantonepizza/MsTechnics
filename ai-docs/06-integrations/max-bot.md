# MAX Bot — интеграция с мессенджером MAX

MAX — мессенджер от VK, российский. Не блокируется РКН. API документировано на [dev.max.ru](https://dev.max.ru).

## Implementation snapshot — 2026-05-05

- Исходящая отправка реализована в `apps.notifications.channels.max.MaxChannel`.
- Endpoint отправки: `{MAX_API_BASE}/messages`, token передаётся как `access_token`.
- Переменные окружения:
  - `MAX_BOT_TOKEN`
  - `MAX_API_BASE`
  - `MAX_WEBHOOK_SECRET`
  - `MAX_TIMEOUT_SEC`
- `MaxChannel` использует `recipient.max_chat_id` или существующее поле `recipient.max_id`.
- Inline-кнопки поддержаны через `context["actions"]`:

```python
context={
    "actions": [
        {"label": "Готово", "callback": "application_done:42"},
    ],
}
```

- Webhook подключён как `POST /api/v1/integrations/max/webhook`.
- Если `MAX_WEBHOOK_SECRET` задан, webhook проверяет `X-MAX-Secret` или `X-Max-Webhook-Secret`.
- Поддержанные входящие команды:
  - `/start <username>` — привязать текущий MAX chat id к `MsUser.max_id`;
  - `/unbind` — отвязать текущий MAX chat id;
  - `/start` — показать подсказку.
- Поддержанный callback:
  - `application_done:<id>` — вызывает `ApplicationService.transition(..., target_status="done")`.

Ограничения:

- Реальный bot token и webhook registration остаются ручным шагом владельца/админа.
- В текущей модели используется `MsUser.max_id`, а не новое `max_chat_id`.
- `accept_departure:<id>` не реализован: в доменной модели нет action/status "accept departure".

---

## Что делает бот

Дублирует функциональность Telegram-бота:
1. Получает уведомления о заявках, переходах, событиях
2. Принимает команды от пользователя: `/start`, `/bind <code>`, `/unbind`, `/status`, `/help`
3. Показывает inline-кнопки (если API поддерживает) для быстрых действий

---

## API MAX

> Предварительный анализ — уточнить по актуальной документации на момент реализации.

Основные endpoint'ы (ориентировочно):
```
POST https://botapi.max.ru/bot<TOKEN>/sendMessage
POST https://botapi.max.ru/bot<TOKEN>/setWebhook
GET  https://botapi.max.ru/bot<TOKEN>/getMe
```

Структура message похожа на Telegram:
```json
{
  "chat_id": "...",
  "text": "...",
  "parse_mode": "Markdown|HTML",
  "reply_markup": { "inline_keyboard": [...] }
}
```

Если API совпадает на 90% с TG — адаптер минимальный.

---

## Архитектура адаптера

```
apps/notifications/channels/max.py

class MaxChannel:
    BASE_URL = "https://botapi.max.ru/bot{token}"

    def __init__(self, settings):
        self._token = settings.MAX_BOT_TOKEN
        self._session = httpx.Client(timeout=10)

    def can_deliver(self, user):
        return bool(user.max_chat_id)

    def deliver(self, user, message):
        url = self.BASE_URL.format(token=self._token) + "/sendMessage"
        r = self._session.post(url, json={
            "chat_id": user.max_chat_id,
            "text": message,
            "parse_mode": "HTML",
        })
        if r.status_code == 200:
            return DeliveryResult.success()
        return DeliveryResult.failure(r.text)
```

---

## Модель

Добавить поле в `MsUser` (через data-migration):
```python
max_chat_id = models.CharField(max_length=64, blank=True, null=True, unique=True, db_index=True)
max_username = models.CharField(max_length=64, blank=True, null=True)
```

Предпочтение пользователя:
```python
preferred_channels = models.JSONField(default=list)  # ["max", "telegram"] — в порядке приоритета
```

Если пусто — используем все доступные.

---

## Webhook для команд

Пишем отдельный endpoint `/api/v1/webhooks/max/` (token в URL для простого auth):
```python
class MaxWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, token):
        if token != settings.MAX_WEBHOOK_TOKEN:
            raise PermissionDenied
        
        update = MaxUpdateParser.parse(request.data)
        handler = self._resolve_handler(update)
        return handler.handle(update)
```

Обработчики команд:
- `/start` → приветствие + инструкция как привязать аккаунт
- `/bind <code>` → код пользователь получает в личном кабинете MsTechnics; бот записывает chat_id к юзеру
- `/unbind` → обнулить `max_chat_id`
- `/status` → показать привязку + активные заявки юзера
- `/help` → список команд

---

## Привязка аккаунта (bind flow)

1. Юзер в `/lk` жмёт «Подключить MAX»
2. Фронт: GET `/api/v1/me/bind-code?channel=max` → `{ code: "A5F3K2" }` (живёт 10 мин)
3. UI показывает инструкцию: «Открой бот @ms_technics_bot в MAX, напиши `/bind A5F3K2`»
4. Бот получает команду → находит код в Redis → связывает `max_chat_id` с юзером
5. Бот: «Готово! Ты привязан к аккаунту Mikhail.»

Код храним в Redis:
```
SET bind_code:A5F3K2 user_id:42 EX 600
```

При использовании — атомарно `GETDEL` + создать запись в БД.

---

## Процессы

### Consumer (из Streams)
`consumer_max.py` — воркер, аналогичный `sender_tg_message.py`:
```python
class MaxConsumer:
    STREAM = "notifications.max"
    GROUP = "max-workers"

    def run(self):
        ...
```

### Webhook
Обычный Django view, работает в рамках WSGI gunicorn. Rate limit: 60/min с 1 IP.

---

## Настройка webhook'а

После деплоя — один раз вызвать:
```bash
curl -X POST "https://botapi.max.ru/bot<TOKEN>/setWebhook" \
  -d "url=https://mstechnics.ru/api/v1/webhooks/max/<SECRET>"
```

Management command:
```python
python manage.py setup_max_webhook
```

---

## Клон логики TG

Существующий `sender_tg_message.py` — 90% переиспользуется. Отличия:
- URL API
- Формат `chat_id` (у MAX может быть string vs int — уточнить)
- `parse_mode` (markdown vs html)
- Лимиты (уточнить)

Выделяем общий базовый класс `BaseMessengerChannel`, наследуем `TelegramChannel` и `MaxChannel`.

---

## Тесты

- Unit: парсинг update'ов с фикстурами
- Integration: fake HTTPX transport с сценариями ответов
- Manual: в test-чат MAX-бота пишем `/bind TEST123`, смотрим что привязался

---

## Rollout

**Фаза 5.1:** написан клиент, работает send_message (без webhook'а — только исходящие)
**Фаза 5.2:** webhook, `/bind` flow
**Фаза 5.3:** в админке — добавить `preferred_channels` у юзеров
**Фаза 5.4:** включить `max` в `NOTIFICATION_CHANNELS`

После 1 недели стабильной работы — объявляем как основной канал, TG — резерв.

---

## Что уточнить у владельца

1. Есть ли уже корпоративный MAX-аккаунт у компании?
2. Кто будет владельцем бота (нужен номер телефона)?
3. Нужны ли inline-кнопки в сообщениях (например, «Принять заявку» прямо из мессенджера)? — это большое расширение, на старте можно пропустить.
