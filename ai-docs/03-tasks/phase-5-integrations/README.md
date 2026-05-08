# Фаза 5 — Integrations

> **Цель:** заменить хрупкую legacy-интеграцию (Telegram-бот, Gmail-парсинг, daily_checker) на стабильный стек с MAX-фолбеком, единым уведомительным движком, gmail-alarms и cleanup legacy.

**Длительность:** ~30 часов
**Кодер:** GPT-кодер (backend)
**Архитектор:** Claude Opus

---

## Контекст и текущее положение

В legacy:
- `sender_tg_message.py` — отдельный воркер, слушает Redis pubsub, отправляет в Telegram. Падает периодически из-за блокировок Telegram в РФ.
- `daily_checker.py` — отдельный воркер, проверяет есть ли просроченные DailyTask, шлёт уведомления в TG.
- `mail/views.py` — Gmail OAuth 2 + IMAP, парсит письма от поставщиков.
- `ManageControl.py` — оркестратор воркеров.

**Проблемы:**
1. **TG регулярно падает** в РФ — нужен фолбек (MAX или email).
2. **MAX-бот** — Mail.ru мессенджер, корпоративный аналог TG, **уже доступен** (владелец подтвердил).
3. **VNNOX (gmail-парсер)** — заявки/восстановления панелей приходят в почту от `service@alimail.vnnox.com`, нужно автоматически создавать `AlarmEvent` (но НЕ заявки — ради защиты от шума).
4. **DailyTask** — оставлен в legacy `zip/models.py` (T-2-fix-002 решит).
5. **Worker'ы вне Django ASGI** — нет structlog, нет shared контекста.

---

## Список задач

### 5.0. Notification redesign

| ID | Задача | Оценка |
|----|--------|--------|
| T-5-001 | Архитектура: `apps/notifications/` — channels + dispatcher | 3ч |
| T-5-002 | Channel: TelegramChannel (через прокси) | 1.5ч |
| T-5-003 | Channel: MaxChannel | 2ч |
| T-5-004 | Channel: EmailChannel (fallback для прода) | 1ч |
| T-5-005 | NotificationDispatcher — выбор channel'а по правилу | 1.5ч |
| T-5-006 | Triggers: 6 правил (заявка создана, в сервис, выполнено, выезд, SLA-просрочено, daily_task) | 2ч |

### 5.1. Telegram-инфра

| ID | Задача | Оценка |
|----|--------|--------|
| T-5-010 | Setup SOCKS5/HTTP-прокси для Telegram (бот через VPN-сервер) | 1.5ч |
| T-5-011 | Заменить `sender_tg_message.py` на новый worker через `apps.notifications` | 1ч |

### 5.2. MAX bot

| ID | Задача | Оценка |
|----|--------|--------|
| T-5-020 | MAX bot setup — регистрация, токен | 0.5ч |
| T-5-021 | MAX bot integration — отправка сообщений | 2ч |
| T-5-022 | Webhook receiver: вернуть статус (например /accept после уведомления о выезде) | 1.5ч |
| T-5-023 | User binding: `MsUser.max_chat_id` сохраняется при первом /start от юзера | 1ч |

### 5.3. Gmail alarms (VNNOX)

| ID | Задача | Оценка |
|----|--------|--------|
| T-5-030 | Gmail-parser: pull новых писем + парсинг VNNOX-формата | 2ч |
| T-5-031 | Создание `AlarmEvent` модели + связь с Display через `vnnox_device_id` | 1.5ч |
| T-5-032 | UI на Display View: панель «VNNOX-алармы» с лентой неразрешённых | 1.5ч |
| T-5-033 | Уведомление мониторщику если аларм висит > N минут | 1ч |

### 5.4. Worker stack rewrite

| ID | Задача | Оценка |
|----|--------|--------|
| T-5-040 | `daily_checker.py` → `apps.workflow.daily_tasks.tasks` через django-q2 или management cmd + cron | 2ч |
| T-5-041 | `ManageControl.py` удалить — supervisor/systemd/docker-compose service per worker | 1.5ч |
| T-5-042 | structlog в воркеры + Sentry capture | 0.5ч |

### 5.5. Cleanup legacy

| ID | Задача | Оценка |
|----|--------|--------|
| T-5-050 | Удалить legacy templates (после деплоя SPA на staging) | 1ч |
| T-5-051 | Удалить legacy views в /control/, /service/, /monitoring/, /zip/, /menu/, /application/, /departure/ | 2ч |
| T-5-052 | Удалить compat-shims (`main/models.py`, `user/models.py`, `zip/models.py`, etc.) — после grep с подтверждением 0 references | 1ч |
| T-5-053 | Удалить `MsServiceControl/` (старая Django settings папка) | 0.5ч |

---

## Граф зависимостей

```
T-2-fix-002 (DailyTask) ─────────► T-5-040 (daily worker rewrite)
                                          │
T-5-001 (notify infra) ──┬──► T-5-002,003,004 (channels) ──► T-5-005 (dispatcher) ──► T-5-006 (triggers)
                         │                                                    │
                         ├──► T-5-010 (TG proxy) ──► T-5-011 (TG worker)      │
                         │                                                    │
                         └──► T-5-020 (MAX setup) ──► T-5-021,022,023 (MAX) ──┤
                                                                              │
T-5-030 (gmail) ──► T-5-031 (alarm model) ──► T-5-032 (UI) ──► T-5-033 (notify)
                                                                              │
                                                                              ▼
                                            После деплоя SPA на staging ──► T-5-050,051,052,053 (cleanup)
```

---

## Что НЕ делать в Фазе 5

- ❌ Не переписывать `mail/views.py` для нового Gmail OAuth — он работает, не трогаем
- ❌ Не отказываться от Telegram целиком — он остаётся как primary, MAX — fallback
- ❌ Не строить custom queue (Celery/RQ) — django-q2 или management commands + cron
- ❌ Не делать Telegram Bot Premium / Voice / etc — только текстовые сообщения

---

## Критерии завершения Фазы 5

- [ ] Telegram через прокси работает стабильно (24h без упавших message'ей)
- [ ] MAX как fallback: если TG не доставлен 30 секунд → MAX
- [ ] 6 типов уведомлений работают
- [ ] VNNOX-алармы создают AlarmEvent, мониторщик видит ленту
- [ ] daily_checker переехал на django-q2 или cron
- [ ] Legacy cleanup: `grep -rn 'from main_menu\|from monitoring\|from control\|from service\|from zip' apps/ frontend/` — пусто
- [ ] `ManageControl.py` удалён, воркеры через docker-compose
- [ ] Coverage ≥ 70% на новом коде
- [ ] Документация по каждой интеграции в `ai-docs/06-integrations/`

---

## Документация интеграций

В `ai-docs/06-integrations/` создать:
- `notifications-redesign.md` — архитектура channel/dispatcher/trigger
- `telegram-russia-workaround.md` — прокси-схема, troubleshooting
- `max-bot.md` — setup, webhook URL, binding
- `gmail-alarms.md` — VNNOX format, regex, маппинг
