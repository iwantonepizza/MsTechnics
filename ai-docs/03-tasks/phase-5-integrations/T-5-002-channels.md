# T-5-002 / T-5-003 / T-5-004. Channels: Telegram + MAX + Email

> **Тип:** integration
> **Приоритет:** P0 (TG, MAX), P2 (Email)
> **Оценка:** 4.5 часа суммарно (1.5 + 2 + 1)
> **Фаза:** 5
> **Статус:** done
> **Взял:** GPT-5 Codex

---

## Зависимости

- **Блокируется:** T-5-001 (BaseChannel)
- **Блокирует:** T-5-005 (Dispatcher)

---

## T-5-002. TelegramChannel

### Settings

```python
# config/settings.py
TELEGRAM_BOT_TOKEN = env('TELEGRAM_BOT_TOKEN')
TELEGRAM_PROXY_URL = env('TELEGRAM_PROXY_URL', default=None)  # 'socks5://user:pass@host:port' или 'http://...'
TELEGRAM_TIMEOUT_SEC = 30
```

### Channel

```python
# apps/notifications/channels/telegram.py
import httpx
import structlog
from django.conf import settings

from .base import BaseChannel, DeliveryResult

logger = structlog.get_logger(__name__)


class TelegramChannel(BaseChannel):
    name = 'telegram'
    
    def can_deliver(self, recipient) -> bool:
        return bool(getattr(recipient, 'telegram_id', None))
    
    def deliver(self, recipient, text: str, *, context: dict = None) -> DeliveryResult:
        token = settings.TELEGRAM_BOT_TOKEN
        proxy = settings.TELEGRAM_PROXY_URL
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        
        try:
            client_kwargs = {'timeout': settings.TELEGRAM_TIMEOUT_SEC}
            if proxy:
                client_kwargs['proxies'] = proxy
            
            with httpx.Client(**client_kwargs) as client:
                response = client.post(url, json={
                    'chat_id': recipient.telegram_id,
                    'text': text,
                    'parse_mode': 'HTML',
                    'disable_web_page_preview': True,
                })
                
                if response.status_code == 200:
                    return DeliveryResult(
                        succeeded=True,
                        error=None,
                        response=response.json(),
                    )
                else:
                    error = response.json().get('description', f'HTTP {response.status_code}')
                    return DeliveryResult(succeeded=False, error=error, response=response.json())
        
        except httpx.TimeoutException:
            return DeliveryResult(succeeded=False, error='timeout', response={})
        except httpx.ProxyError as e:
            logger.warning('telegram_proxy_error', error=str(e))
            return DeliveryResult(succeeded=False, error=f'proxy: {e}', response={})
        except Exception as e:
            return DeliveryResult(succeeded=False, error=str(e), response={})
```

---

## T-5-003. MaxChannel

> MAX (Mail.ru Messenger) — корпоративный мессенджер, владелец подтвердил наличие.
> 
> **API docs:** https://max.ru/developers (или альтернативные docs владельца)
> 
> Если API схож с Telegram (а это часто так у "TG-клонов") — `MaxChannel` практически копия `TelegramChannel`.

### Settings

```python
MAX_BOT_TOKEN = env('MAX_BOT_TOKEN', default=None)
MAX_API_BASE = env('MAX_API_BASE', default='https://api.max.ru/v1')
MAX_TIMEOUT_SEC = 30
```

### Channel

```python
class MaxChannel(BaseChannel):
    name = 'max'
    
    def can_deliver(self, recipient) -> bool:
        return bool(getattr(recipient, 'max_chat_id', None))
    
    def deliver(self, recipient, text: str, *, context: dict = None) -> DeliveryResult:
        if not settings.MAX_BOT_TOKEN:
            return DeliveryResult(succeeded=False, error='MAX_BOT_TOKEN не задан', response={})
        
        try:
            with httpx.Client(timeout=settings.MAX_TIMEOUT_SEC) as client:
                response = client.post(
                    f'{settings.MAX_API_BASE}/messages',
                    json={
                        'chat_id': recipient.max_chat_id,
                        'text': text,
                    },
                    headers={'Authorization': f'Bearer {settings.MAX_BOT_TOKEN}'},
                )
                
                if response.status_code in (200, 201):
                    return DeliveryResult(succeeded=True, error=None, response=response.json())
                else:
                    return DeliveryResult(
                        succeeded=False,
                        error=f'HTTP {response.status_code}: {response.text[:200]}',
                        response={'status': response.status_code},
                    )
        except Exception as e:
            return DeliveryResult(succeeded=False, error=str(e), response={})
```

**Заметка:** точные endpoints MAX зависят от их API. Перед началом — спросить владельца / проверить docs. Если API сильно отличается — адаптировать. Архитектура канала (`can_deliver` + `deliver` → DeliveryResult) — стабильна.

---

## T-5-004. EmailChannel

```python
class EmailChannel(BaseChannel):
    name = 'email'
    
    def can_deliver(self, recipient) -> bool:
        return bool(getattr(recipient, 'email', None))
    
    def deliver(self, recipient, text: str, *, context: dict = None) -> DeliveryResult:
        from django.core.mail import send_mail
        try:
            sent = send_mail(
                subject='[MsTechnics] Уведомление',
                message=text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                fail_silently=False,
            )
            return DeliveryResult(
                succeeded=sent > 0,
                error=None if sent else 'Send mail returned 0',
                response={'sent_count': sent},
            )
        except Exception as e:
            return DeliveryResult(succeeded=False, error=str(e), response={})
```

---

## Критерии приёмки

### T-5-002 (Telegram)

- [ ] Канал отправляет сообщение через прокси (если настроен)
- [ ] Возвращает `DeliveryResult` с правильным error на проблемах прокси
- [ ] Поддерживает HTML parse_mode (для жирности и ссылок)
- [ ] Тест с mock-сервером (`httpx_mock` или responses)

### T-5-003 (MAX)

- [ ] Канал отправляет, если задан токен
- [ ] Если токен отсутствует — возвращает error без request
- [ ] Тест с mock-сервером

### T-5-004 (Email)

- [ ] Канал использует Django send_mail
- [ ] Тест с `django.core.mail.outbox`

---

## Что НЕ делать

- НЕ хранить токены в коде — только через env
- НЕ делать retry на уровне канала — это работа dispatcher'а через django-q2
- НЕ блокировать на синхронной отправке — но в данном случае воркер тоже синхронный, ок

---

## Конфиг прокси (для T-5-010)

```bash
# .env пример
TELEGRAM_BOT_TOKEN=1234:abcdef
TELEGRAM_PROXY_URL=socks5://user:pass@vpn.example.com:1080

MAX_BOT_TOKEN=...
MAX_API_BASE=https://api.tamtam.chat/  # пример (если MAX = TamTam)
```
