# T-5-020 / T-5-021 / T-5-022 / T-5-023. MAX bot — setup, integration, webhook, binding

> **Тип:** integration
> **Приоритет:** P0
> **Оценка:** 5 часов (0.5 + 2 + 1.5 + 1)
> **Фаза:** 5
> **Статус:** review
> **Взял:** GPT-5 Codex

---

## Контекст

MAX — Mail.ru Messenger, владелец подтвердил что использует. Нужен fallback для TG.

---

## Зависимости

- **Блокируется:** T-5-001 (NotificationDispatcher), T-5-003 (MaxChannel)

---

## T-5-020. MAX bot setup

### Что сделать

1. **У владельца взять:**
   - MAX bot token (через `@MasterBot` или developer-portal)
   - URL API base
   - Webhook secret (если есть)

2. **Зарегистрировать webhook:**
   ```bash
   curl -X POST 'https://api.max.ru/v1/bot{token}/setWebhook' \
     -d 'url=https://mstechnics.ru/api/v1/integrations/max/webhook'
   ```
   (точный путь URL зависит от MAX API)

3. **Добавить в `.env.example`:**
   ```bash
   MAX_BOT_TOKEN=
   MAX_API_BASE=https://api.max.ru/v1   # или другое
   MAX_WEBHOOK_SECRET=
   ```

### Критерии

- [ ] Бот зарегистрирован у владельца, токен у него
- [ ] Webhook ходит на наш endpoint (логи показывают request от MAX)
- [ ] `.env.example` обновлён

---

## T-5-021. MAX integration — отправка

Реализуется внутри `apps/notifications/channels/max.py` (см. T-5-003).

Дополнительно на этом шаге:

- **Поддержка форматирования:** MAX может поддерживать markdown / специальные сущности — проверить и в `template.text` использовать совместимое форматирование.
- **Кнопки inline:** если MAX-бот поддерживает inline keyboard (большинство таких ботов поддерживает) — использовать их для T-5-022 quick-actions.

```python
# apps/notifications/channels/max.py
def deliver(self, recipient, text, *, context=None):
    payload = {
        'chat_id': recipient.max_chat_id,
        'text': text,
    }
    
    # Если в context есть callback'и — добавить inline keyboard
    if context and 'actions' in context:
        payload['reply_markup'] = {
            'inline_keyboard': [[
                {'text': a['label'], 'callback_data': a['callback']}
                for a in context['actions']
            ]]
        }
    
    # ... отправка как в T-5-003
```

### Критерии

- [ ] MaxChannel отправляет сообщения с inline кнопками
- [ ] Тест с mock'ом

---

## T-5-022. Webhook receiver

### Цель

Когда юзер нажимает кнопку в MAX-боте (например «Принять выезд»), MAX шлёт callback нам через webhook. Мы обрабатываем и делаем доменное действие.

### Endpoints

```
POST /api/v1/integrations/max/webhook   # incoming MAX callback
```

### Implementation

`apps/integrations/max/views.py`:

```python
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
import json
import structlog

logger = structlog.get_logger(__name__)


@csrf_exempt
@require_POST
def max_webhook(request):
    # 1. Verify signature (if MAX supports)
    secret = request.headers.get('X-MAX-Secret', '')
    if secret != settings.MAX_WEBHOOK_SECRET:
        return HttpResponse(status=403)
    
    # 2. Parse payload
    try:
        payload = json.loads(request.body)
    except ValueError:
        return HttpResponse(status=400)
    
    update_type = payload.get('update_type')
    
    if update_type == 'message_callback':
        callback_data = payload['callback']['payload']
        chat_id = payload['callback']['user']['user_id']
        _handle_callback(callback_data, chat_id, payload)
    
    elif update_type == 'message_created':
        # Юзер написал боту → /start или ручное сообщение
        _handle_user_message(payload)
    
    return HttpResponse(status=200)


def _handle_callback(callback_data: str, chat_id: int, payload: dict):
    """Парсим callback типа 'accept_departure:<id>' и выполняем."""
    if ':' not in callback_data:
        return
    
    action, _, ref = callback_data.partition(':')
    
    if action == 'accept_departure':
        _accept_departure(int(ref), chat_id)
    elif action == 'application_done':
        _mark_application_done(int(ref), chat_id)
    # ...


def _accept_departure(departure_id: int, max_chat_id: int):
    """Принять выезд через FSM."""
    from apps.workflow.departures.models import Departure
    from apps.core.users.models import MsUser
    from apps.workflow.departures.services import departure_service
    
    user = MsUser.objects.filter(max_chat_id=max_chat_id).first()
    if not user:
        return
    
    try:
        departure = Departure.objects.get(id=departure_id)
        departure_service.accept(departure, user=user)
    except Exception as e:
        logger.warning('max_webhook_accept_failed', error=str(e))


def _handle_user_message(payload: dict):
    """Обработка /start и других команд."""
    text = payload.get('message', {}).get('text', '')
    chat_id = payload.get('message', {}).get('user', {}).get('user_id')
    
    if text.startswith('/start'):
        # /start <username> или /start <token>
        # — это T-5-023 (binding)
        ...
```

### URL

```python
# apps/integrations/max/urls.py
from django.urls import path
from .views import max_webhook

urlpatterns = [
    path('webhook', max_webhook, name='max-webhook'),
]
```

В `config/urls.py`:
```python
path('api/v1/integrations/max/', include('apps.integrations.max.urls')),
```

### Критерии

- [ ] Webhook endpoint валидирует signature
- [ ] callback `accept_departure:<id>` работает
- [ ] callback `application_done:<id>` работает
- [ ] Логи всех incoming через structlog
- [ ] Тест с fake-payload

---

## T-5-023. User binding

### Цель

Привязать `MsUser.max_chat_id`. Юзер пишет `/start <username>` боту — мы связываем chat_id с username'ом.

### Flow

1. Админ отправляет юзеру: «Зайди в бот @MsTechBot и напиши `/start <твой_username>`»
2. Юзер пишет это в MAX
3. Webhook получает `message_created` с text = `/start ivan_petrov`
4. Бэкенд: ищет MsUser с username='ivan_petrov', сохраняет `max_chat_id=<chat_id из payload>`
5. Бот отвечает: «Привязка успешна, теперь будешь получать уведомления»

### Implementation

```python
def _handle_user_message(payload: dict):
    text = payload['message']['text']
    chat_id = payload['message']['user']['user_id']
    
    if text.startswith('/start '):
        username = text[len('/start '):].strip()
        from apps.core.users.models import MsUser
        try:
            user = MsUser.objects.get(username=username)
            user.max_chat_id = str(chat_id)
            user.save(update_fields=['max_chat_id'])
            _send_max_message(chat_id, f'✅ Привязка успешна. Привет, {user.username}!')
        except MsUser.DoesNotExist:
            _send_max_message(chat_id, '❌ Пользователь не найден')
    elif text == '/start':
        _send_max_message(chat_id, 'Используй: `/start <твой_username>`')
```

### Безопасность

- **Не привязываем без подтверждения** — username должен быть точным
- **Опционально:** одноразовый токен `/start abc123def`, генерируемый юзером в `/profile` web-UI. Безопаснее, но сложнее (нужен UI).

В первой итерации — **достаточно `/start <username>`**, бот спросит подтверждение, юзер подтвердит. Если уже есть `max_chat_id` — бот просит ввести `/unbind` сначала.

### Критерии

- [ ] `/start <username>` привязывает (если username корректный)
- [ ] `/unbind` отвязывает
- [ ] При попытке привязать к занятому username — отказ
- [ ] Поле `MsUser.max_chat_id` уникальное (`unique=True, null=True, blank=True`)
- [ ] Тесты

---

## Что НЕ делать

- НЕ хранить max_chat_id в plain text в логах (PII)
- НЕ полагаться только на `/start` — добавить web-UI binding в /profile в Фазе 4 если важно
- НЕ обрабатывать сообщения от юзеров без знака команды — игнорировать или вежливо отвечать «Я бот для уведомлений, не общаюсь»
