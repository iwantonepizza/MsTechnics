# Telegram в РФ — workaround для блокировок

## Контекст

С марта-апреля 2024 Роскомнадзор периодически ограничивает доступ к `api.telegram.org` и `*.telegram.org` с российских IP. Работает нестабильно: часть запросов проходит, часть падает с connection reset или timeout.

**Результат для нас:** бот `sender_tg_message.py` иногда молчит — сообщения владельцу не приходят, часть заявок пропадает из-под радара.

---

## Варианты решения

### Вариант A — SOCKS5-прокси через зарубежный VPS (рекомендую)

**Как:**
1. Арендуем копеечный VPS в Европе/Азии ($3-5/мес на Hetzner/DigitalOcean/Scaleway)
2. Поднимаем на нём `dante-server` или `3proxy` — SOCKS5
3. В `settings.py` добавляем `TELEGRAM_PROXY_URL`
4. `python-telegram-bot`, `aiohttp`, `httpx` — все поддерживают `proxy`

**Плюсы:**
- Стабильно
- Низкая задержка (Европа — ~30-60мс с России)
- Прозрачно для кода (один флаг)

**Минусы:**
- VPS надо платить
- Прокси может тоже заблокироваться (редко, но бывает)

**Цена:** ~$5/мес + 1ч настройки.

### Вариант B — MTProto-прокси

Официально поддерживается Telegram'ом. `MTProxy` от Telegram — open source.

**Плюсы:** рассчитан именно на обход блокировок.
**Минусы:** работает для клиентов TG (мобилка), для Bot API — не идеально. Bot API идёт через HTTPS, а не через MTProto.

**Не подходит для нашего случая.**

### Вариант C — mirror / reverse proxy на своём сервере в другой стране

Если у компании уже есть серверы за границей, поднимаем nginx с proxy_pass на `api.telegram.org`. Локально ходим на свой домен.

**Плюсы:** полный контроль.
**Минусы:** сложнее поддерживать, риск блокировки по домену у Telegram.

### Вариант D — переход на MAX как основной канал

См. `max-bot.md`. MAX — VK-шный мессенджер, в РФ не блокируется. Хорошая идея как основной канал, но:
- Пользователям надо установить MAX и привязать аккаунт
- Переход не мгновенный
- TG оставляем как резервный для гиков

**Рекомендация:** делаем и A, и D. SOCKS5 — чтобы починить TG уже сегодня. MAX — как основной канал через месяц.

---

## Реализация Варианта A

### Статус в репозитории на 2026-05-05

- `Config/settings.py` читает `TELEGRAM_PROXY_URL` и `TELEGRAM_TIMEOUT_SEC` из окружения.
- `apps.notifications.channels.telegram.TelegramChannel` отправляет Telegram Bot API запросы через `httpx.Client(proxy=...)`, если `TELEGRAM_PROXY_URL` задан.
- Для SOCKS5 установлен runtime requirement `httpx[socks]` / `socksio`.
- `.env.example` содержит пример `TELEGRAM_PROXY_URL=socks5://user:password@your-vps.example.com:1080`.
- Health-check: `python scripts/check_telegram_proxy.py`.

Переменные для проверки:

```bash
TELEGRAM_BOT_TOKEN=...
TELEGRAM_PROXY_URL=socks5://user:password@host:1080
TELEGRAM_TIMEOUT_SEC=15
python scripts/check_telegram_proxy.py
```

Успешный ответ:

```json
{"ok": true, "proxy": "socks5://user:***@host:1080", "telegram_user": "bot_username"}
```

### 1. Поднять SOCKS5

На VPS, Ubuntu 24:

```bash
sudo apt install dante-server
```

`/etc/danted.conf`:
```
logoutput: syslog
internal: 0.0.0.0 port=1080
external: eth0
method: username
user.privileged: root
user.unprivileged: nobody
user.libwrap: nobody

client pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    log: connect disconnect
}

socks pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    protocol: tcp udp
    log: connect disconnect error
}
```

Пользователь:
```bash
sudo useradd -r -s /bin/false msproxy
sudo passwd msproxy
```

```bash
sudo systemctl enable --now danted
```

Файрвол:
```bash
ufw allow 1080/tcp
```

(по-хорошему разрешаем только IP нашего прод-сервера — `ufw allow from X.X.X.X to any port 1080`).

### 2. Настроить в Django

```python
# settings.py
TELEGRAM_PROXY_URL = env("TELEGRAM_PROXY_URL", default=None)
# env: TELEGRAM_PROXY_URL=socks5://msproxy:PASSWORD@VPS_IP:1080
```

### 3. Использовать в коде

`apps/notifications/channels/telegram.py`:
```python
from telegram import Bot
from telegram.request import HTTPXRequest

class TelegramChannel:
    def __init__(self, settings):
        request = HTTPXRequest(
            proxy_url=settings.TELEGRAM_PROXY_URL,
            connect_timeout=10,
            read_timeout=10,
        )
        self._bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, request=request)

    def deliver(self, user, message):
        try:
            self._bot.send_message(chat_id=user.telegram_id, text=message, parse_mode="HTML")
            return DeliveryResult.success()
        except TelegramError as exc:
            logger.error("telegram_delivery_failed", user_id=user.id, exc=exc)
            return DeliveryResult.failure(str(exc))
```

### 4. Healthcheck

Отдельный процесс или Django management command:
```python
class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        channel = TelegramChannel(settings)
        test_chat = settings.TELEGRAM_HEALTHCHECK_CHAT_ID
        msg = f"ping from {socket.gethostname()} at {datetime.now()}"
        try:
            channel._bot.send_message(chat_id=test_chat, text=msg)
            logger.info("tg_healthcheck_ok")
        except Exception as exc:
            logger.error("tg_healthcheck_failed", exc=exc)
            sentry_sdk.capture_message("TG healthcheck failed: " + str(exc))
```

Запускать каждые 5 минут через cron / systemd timer.

---

## Cost

- VPS: $5/мес ≈ 450₽/мес (по курсу Apr 2026 — уточни)
- Телеграм-канал для healthcheck — бесплатно

Заметно ниже потерь от пропущенных заявок.

---

## Риски и как их митигировать

| Риск | Митигация |
|---|---|
| VPS заблокируют в РФ | Имеем 2 VPS в разных странах, в settings — список, fallback |
| SOCKS5 credentials утекут в логи | Пароль всегда из env, маскируем при логировании URL |
| Прокси перегружен | Rate limit на сторону `TelegramChannel` — не более N/sec |
| Telegram API отказал не из-за РФ | Retry + DLQ работают одинаково |
| Упал healthcheck — не увидим | Sentry + alert в Slack / письмо |

---

## Когда это делать

Хотфикс на текущем проде — **Фаза 1** (задача `T-1-012-telegram-healthcheck` + `T-1-013-telegram-proxy`). Не ждём фазы 5, потому что бизнес болит прямо сейчас.

После переноса на Streams в Фазе 5 — остаётся та же логика, только вызов канала происходит из Streams-consumer'а.
