# T-5-010 / T-5-011. Telegram через прокси + замена sender_tg_message.py

> **Тип:** integration / cleanup
> **Приоритет:** P0
> **Оценка:** 2.5 часа (1.5 + 1)
> **Фаза:** 5
> **Статус:** done
> **Взял:** GPT-5 Codex

---

## T-5-010. SOCKS5/HTTP прокси для Telegram

### Цель

Российские IP блокируются Telegram API. Нужен прокси (SOCKS5 или HTTP) на VPN-сервере, через который ходит наш бот.

### Что сделать

**1. Установить прокси-сервер на VDS вне РФ.**

Опции:
- **3proxy** — лёгкий, поддерживает SOCKS5
- **Dante** — стандарт SOCKS5
- **Squid** — HTTP/HTTPS forward proxy

Рекомендация: **3proxy с SOCKS5 + auth**. Конфиг:

```bash
# /etc/3proxy/3proxy.cfg на VPS
nserver 1.1.1.1
nserver 8.8.8.8

users mstechtg:CL:secret_password_change_me
auth strong
allow mstechtg

socks -p1080
maxconn 50
log /var/log/3proxy/3proxy.log
```

**2. В .env проекта:**

```bash
TELEGRAM_PROXY_URL=socks5://mstechtg:secret_password_change_me@your-vps.com:1080
```

**3. httpx требует:**

```python
pip install httpx[socks]
# или в pyproject.toml:
"httpx[socks]>=0.27"
```

**4. Health-check скрипт.**

```python
# scripts/check_telegram_proxy.py
import httpx, os, sys

token = os.environ['TELEGRAM_BOT_TOKEN']
proxy = os.environ['TELEGRAM_PROXY_URL']

try:
    with httpx.Client(proxies=proxy, timeout=15) as c:
        r = c.get(f'https://api.telegram.org/bot{token}/getMe')
        print(r.json())
        sys.exit(0)
except Exception as e:
    print(f'FAIL: {e}', file=sys.stderr)
    sys.exit(1)
```

Запускать в CI и в monitoring-cron на проде.

### Критерии

- [ ] VPS с 3proxy / Dante настроен
- [ ] `TELEGRAM_PROXY_URL` в `.env.example` с комментарием
- [ ] `scripts/check_telegram_proxy.py` работает
- [ ] Прокси-credentials в **password manager** (не в репо!)
- [ ] Документация в `ai-docs/06-integrations/telegram-russia-workaround.md`

---

## T-5-011. Заменить sender_tg_message.py

### Что сейчас

`sender_tg_message.py` — отдельный воркер, слушает Redis pubsub, шлёт в TG. Это legacy, надо сменить на использование нового стека `apps.notifications`.

### Что сделать

**Подход:** старый воркер удаляем, отправка идёт прямо в `notification_dispatcher.dispatch()` синхронно из triggers (T-5-006). Если хочется async — поставим django-q2 в T-5-040, но сейчас sync OK для ~100 notifications/час.

**Шаги:**

1. **Блок снят владельцем проекта 2026-05-05.** Старый prod остаётся на старой версии до ручного переключения, в новой ветке legacy worker можно убирать.

2. **Удалить файлы:**
   ```bash
   git rm sender_tg_message.py
   git rm sorting_message.py  # если только под TG-pubsub
   ```

   По факту `sorting_message.py` пока оставлен как compat shim, потому его ещё импортируют legacy modules `application`, `zip`, `main`.

3. **Обновить docker-compose.yml** — убрать service `tg_sender`.

4. **Удалить `ManageControl.py`** если он только для legacy workers (см. T-5-041).

5. **Smoke test:**
   - Создать заявку через API
   - Проверить что уведомление пришло в TG получателю

### Критерии

- [x] `sender_tg_message.py` удалён
- [x] docker-compose не содержит tg_sender
- [ ] При создании заявки — уведомление приходит контролёрам в TG
- [ ] При сбое прокси — fallback на MAX (T-5-005)
- [x] Тесты Notification flow зелёные

---

## Что НЕ делать

- НЕ оставлять старый воркер «на всякий случай» — два пути доставки = двойные уведомления
- НЕ переключать prod на новую ветку без проверенных env `TELEGRAM_BOT_TOKEN`, `TELEGRAM_PROXY_URL`, `MAX_*`
- НЕ хранить proxy-пароль в репо
