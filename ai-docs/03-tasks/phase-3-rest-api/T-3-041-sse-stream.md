# T-3-041. SSE stream для real-time

> **Тип:** API / infra
> **Приоритет:** P1
> **Оценка:** 2 часа
> **Фаза:** 3
> **Статус:** done

---

## Цель

Server-Sent Events стрим. Фронт подписывается, при transitions / panel changes / departure-events получает push-сообщения, инвалидирует кэш TanStack Query.

Это **проще, чем WebSocket**: один HTTP-коннект, текстовый протокол, читается через `EventSource` API — нативно в браузере.

---

## Зависимости

- **Блокируется:** T-3-031 (publishing на transitions), T-3-040 (тот же сериализатор)
- **Блокирует:** Фаза 4 — фронтовый `useEventSource` хук

---

## Архитектура

```
┌─────────────────────┐
│  Backend write      │
│  (transition/etc)   │
└──────────┬──────────┘
           │
           ▼
   ActivityLog.create
           │
           │  (в transaction.on_commit)
           ▼
   redis.xadd("events:user:42", {...})
           │
           ▼
   ┌───────────────────┐
   │  SSE View         │
   │  /api/v1/events/  │
   │  stream/          │
   └───────────────────┘
           │
           │  blocking xread
           ▼
       Browser EventSource
```

**Redis Streams**, не Pub/Sub:
- Pub/Sub теряет события если SSE временно отключён
- Streams сохраняет N последних событий, при reconnect клиент перечитывает с last-id

---

## Эндпоинт

```
GET /api/v1/events/stream
    Accept: text/event-stream
    Authorization: Bearer <access>     # OR ?token=<short-lived>

Response: text/event-stream

event: application.transitioned
id: 1745492391-0
data: {"application_id": 42, "state_from": "sent_to_control", "state_to": "apply_in_control", ...}

event: panel.condition_changed
id: 1745492395-0
data: {...}

: heartbeat                             # каждые 15 секунд для keep-alive
```

---

## Что нужно сделать

### Шаг 1. Publisher

`apps/notifications/sse.py`:

```python
"""SSE publisher: публикует события в Redis Stream для каждого юзера.

Использование:
    from apps.notifications.sse import sse_publisher
    sse_publisher.publish(
        recipient_user_ids=[1, 5, 12],
        event_type='application.transitioned',
        payload={'application_id': 42, ...},
    )
"""
import json
from typing import Iterable

import redis
from django.conf import settings
import structlog

logger = structlog.get_logger(__name__)


class SSEPublisher:
    """Публикация в Redis Streams: один stream на user_id."""
    STREAM_PREFIX = 'sse:user:'
    MAXLEN = 100  # хранить последние 100 событий
    
    def __init__(self, redis_url: str = None):
        self._redis = redis.from_url(redis_url or settings.REDIS_URL)
    
    def publish(
        self,
        *,
        recipient_user_ids: Iterable[int],
        event_type: str,
        payload: dict,
    ):
        data = json.dumps(payload, default=str)
        for uid in recipient_user_ids:
            try:
                self._redis.xadd(
                    name=f'{self.STREAM_PREFIX}{uid}',
                    fields={'event_type': event_type, 'data': data},
                    maxlen=self.MAXLEN,
                    approximate=True,
                )
            except Exception as e:
                logger.error('sse_publish_failed', user_id=uid, exc=str(e))


sse_publisher = SSEPublisher()
```

### Шаг 2. Хук в FSM / PanelMover

В `application_service.transition` (T-3-031) добавить публикацию:

```python
def transition(self, ...):
    # ... после atomic:
    
    # Кому отправить? Юзеры с допуском к городу + ролью отдела
    recipients = self._compute_recipients(application, target_state)
    
    sse_publisher.publish(
        recipient_user_ids=recipients,
        event_type='application.transitioned',
        payload={
            'application_id': application.id,
            'display_slug': application.display.slug,
            'state_from': old_status.name,
            'state_to': target_state,
            'actor_username': user.username,
        },
    )
    
    return application

def _compute_recipients(self, app, target_state) -> list[int]:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # base: все у кого есть доступ к городу + ключевые роли
    return list(
        User.objects.filter(
            allowed_city=app.display.city,
            permission__in=['monitoring', 'control', 'service', 'admin', 'all'],
        ).values_list('id', flat=True)
    )
```

В `panel_mover.change_*` — аналогично, но `event_type='panel.condition_changed'` etc.

### Шаг 3. SSE View

`apps/interface/api/v1/events/views.py`:

```python
import json
import time
from typing import Iterator

from django.conf import settings
from django.http import StreamingHttpResponse
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
import redis
import structlog

logger = structlog.get_logger(__name__)
HEARTBEAT_INTERVAL_SECONDS = 15
BLOCK_MS = 5000


class SSEStreamView(APIView):
    """Серверные события через text/event-stream.
    
    Аутентификация: через Authorization header (как обычно) или через ?token=<jwt> query-param,
    т.к. EventSource в браузере не поддерживает кастомные заголовки.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_authenticators(self):
        # Поддержка ?token= для browser EventSource
        token = self.request.GET.get('token') if hasattr(self, 'request') else None
        if token:
            return [_QueryTokenAuthentication()]
        return super().get_authenticators()
    
    @extend_schema(
        tags=['events'],
        summary='SSE поток real-time событий',
        description=(
            'EventSource-совместимый поток. Browser использует ?token=<jwt> для аутентификации '
            '(EventSource API не поддерживает custom headers).'
        ),
        responses={200: OpenApiResponse(description='text/event-stream')},
    )
    def get(self, request):
        return StreamingHttpResponse(
            self._event_stream(request),
            content_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',  # nginx — отключить буферизацию
            },
        )
    
    def _event_stream(self, request) -> Iterator[bytes]:
        user_id = request.user.id
        stream_name = f'sse:user:{user_id}'
        last_id = '$'  # начинаем с самых новых, не перечитываем историю
        
        # Опциональный last-event-id из заголовка (resume после reconnect)
        if last_event_id := request.META.get('HTTP_LAST_EVENT_ID'):
            last_id = last_event_id
        
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        last_heartbeat = time.time()
        
        try:
            while True:
                # Блокирующий read с таймаутом
                events = r.xread({stream_name: last_id}, block=BLOCK_MS, count=10)
                
                if events:
                    for stream_key, messages in events:
                        for msg_id, fields in messages:
                            yield self._format_sse(
                                event_type=fields['event_type'],
                                data=fields['data'],
                                event_id=msg_id,
                            ).encode()
                            last_id = msg_id
                
                # Heartbeat
                if time.time() - last_heartbeat > HEARTBEAT_INTERVAL_SECONDS:
                    yield b': heartbeat\n\n'
                    last_heartbeat = time.time()
        
        except (GeneratorExit, ConnectionResetError):
            logger.info('sse_disconnected', user_id=user_id)
        except Exception as e:
            logger.error('sse_error', user_id=user_id, exc=str(e))
    
    @staticmethod
    def _format_sse(event_type: str, data: str, event_id: str = None) -> str:
        lines = []
        if event_id:
            lines.append(f'id: {event_id}')
        lines.append(f'event: {event_type}')
        # data может быть многострочной
        for line in data.splitlines():
            lines.append(f'data: {line}')
        lines.append('')  # blank line — конец события
        lines.append('')
        return '\n'.join(lines)


class _QueryTokenAuthentication(JWTAuthentication):
    def authenticate(self, request):
        token = request.GET.get('token')
        if not token:
            return None
        validated = self.get_validated_token(token)
        return self.get_user(validated), validated
```

### Шаг 4. URLs

```python
# apps/interface/api/v1/events/urls.py
from django.urls import path
from .views import SSEStreamView

urlpatterns = [
    path('events/stream', SSEStreamView.as_view(), name='events-stream'),
]
```

### Шаг 5. WSGI vs ASGI

**Важно:** SSE требует **долгоживущих соединений**. На gunicorn (sync workers) каждое подключение блокирует worker. Решения:
- gunicorn с `gevent` workers: `gunicorn config.wsgi --worker-class gevent --workers 4 --worker-connections 1000`
- ИЛИ перейти на ASGI с uvicorn для SSE-эндпоинта (но остальное — оставить на WSGI)

**Простой вариант:** gevent workers. Документировать в `infra/`:

```ini
# /etc/systemd/system/mstechnics-web.service
ExecStart=/app/.venv/bin/gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --worker-class gevent \
    --workers 4 \
    --worker-connections 1000 \
    --timeout 120
```

Добавить в `requirements.txt` / `pyproject.toml`:
```toml
"gevent>=23.0",
```

### Шаг 6. Тесты

E2E через `httpx-sse` или ручной curl:

```bash
# Получаем access token
ACCESS=$(curl -s -X POST localhost:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"misha","password":"p"}' | jq -r '.access')

# Запускаем SSE
curl -N "localhost:8000/api/v1/events/stream?token=$ACCESS"

# В другом терминале — делаем transition заявки.
# В первом — должно прилететь событие.
```

Юнит-тесты на _format_sse, на publisher.publish, на _compute_recipients.

---

## Критерии приёмки

- [ ] `SSEPublisher` публикует в `sse:user:<id>` Redis Stream
- [ ] FSM-сервис вызывает publish после atomic commit
- [ ] `panel_mover.change_*` тоже публикует
- [ ] `/api/v1/events/stream` возвращает text/event-stream
- [ ] Поддержка `?token=<jwt>` для browser EventSource
- [ ] Heartbeat каждые 15 секунд
- [ ] Корректный disconnect (не блокирует другие запросы)
- [ ] gevent workers в `infra/` документированы
- [ ] Минимум: ручной smoke-test через curl, plus unit на publisher

---

## Что НЕ делать

- **НЕ используй** WebSocket — overkill для одностороннего push
- **НЕ держи** все Stream'ы (sse:user:*) вечно — `MAXLEN=100` обрезает
- **НЕ блокируй** worker'ы синхронной gunicorn — обязательно gevent
- **НЕ публикуй** PII в payload — только id'шники, фронт делает запрос за деталями
- **НЕ публикуй** того же юзера, который сделал action — anti-flicker (опционально)

---

## Известные подводные камни

- **nginx** буферизирует SSE по дефолту → `X-Accel-Buffering: no` обязателен в response header И в nginx config (`proxy_buffering off;`)
- **CloudFlare** проксирует SSE 100 секунд → нужен heartbeat чаще, чем у нас (или отключить CF на этом endpoint)
- **EventSource** auto-reconnect — браузер сам делает retry. Сервер должен поддержать `Last-Event-ID` header для resume
- **Время жизни access token (15 мин)** меньше чем долгое SSE-соединение → клиент должен переподключаться при истечении токена. Реализовать на фронте.
