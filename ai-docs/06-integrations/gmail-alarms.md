# Gmail / VNNOX Alarms — парсер писем

## Implementation snapshot — 2026-05-05

Новая реализация живёт в `apps.integrations.gmail_alarms`.

Сделано:

- Parser: `apps.integrations.gmail_alarms.parsers.parse_alarm_email`.
- Model: `apps.integrations.gmail_alarms.models.AlarmEvent`.
- Mapping:
  - `Display.vnnox_device_id` сопоставляется с `AlarmRecord.device_id`;
  - `receiving_card_no` переводится в `Cell` через `row/col`;
  - `panel` берётся из найденной `Cell`.
- Gmail pull command: `python manage.py pull_vnnox_alarms`.
- Unresolved notification command: `python manage.py check_unresolved_alarms`.
- API: `GET /api/v1/displays/{slug}/alarms/?resolved=false&limit=50`.
- UI: вкладка `VNNOX` в `DisplayViewPage`.
- Уведомление о висящем аларме: template `vnnox_alarm_unresolved`, threshold `VNNOX_ALARM_NOTIFY_THRESHOLD_MINUTES`.

Важное продуктовое правило:

**Заявки из VNNOX-алармов не создаются автоматически.** UI только открывает `CreateApplicationModal` с prefill-комментарием. Это сделано, чтобы VNNOX noise не создавал лишние заявки.

Ограничения:

- Реальный Gmail OAuth остаётся legacy через `Config/token.pickle`; новый код его переиспользует.
- Реальные письма владельца в репо не лежат; parser покрыт synthetic fixtures по формату карточки.
- Миграционный dry-run локально блокируется существующим project migration graph `KeyError: 'display'`.

---

## Что это

Существующее приложение `mail/` парсит письма от китайского VNNOX (контроллер LED-экранов), который шлёт alerts о сбоях оборудования на email. Сейчас:

1. Аутентификация через Google OAuth2 (файл `Config/client_secret.json` — **скомпрометирован, см. SEC-001**)
2. Token хранится в `Config/token.pickle` — **в репо**
3. `mail/utils.py` — `get_emails()` вызывается вручную из suporuser меню
4. Создаёт `Alarm` / `GmailMessage` в БД
5. Дальше — не очень ясная логика, что происходит дальше

**Проблемы:**

- Секреты в репо (критично, исправляем в Фазе 1)
- Ручной триггер вместо периодического опроса
- Нет лимита на количество выкачиваемых писем за раз — при долгом простое система зависнет
- Нет de-dup'а — одно письмо может быть обработано дважды
- Нет связи между `Alarm` и `Application` — мониторщик не видит удобного ручного пути от аларма к заявке

---

## Целевое поведение

1. **Периодический poll** каждые 15 минут (systemd timer / cron). При появлении нового письма — создать `AlarmEvent`, найти подходящий `Display` / `Cell` / `Panel`.
2. **Идемпотентность:** по `message_id` от Gmail.
3. **Обработка ошибок:** сбой парсинга → письмо помечается как `parse_failed`, но не теряется. Лог в structlog, алерт в sentry.
4. **OAuth через IMAP + app password** как альтернатива (проще в настройке и секретах).
5. **Ручное создание заявки:** мониторщик видит VNNOX-аларм на экране и сам решает, создавать ли заявку.

---

## Варианты аутентификации

### Вариант A — Google OAuth (текущий)
- Клиент OAuth скачивает `client_secret.json`, пользователь проходит consent screen
- После — `token.pickle` с refresh token
- Работает, но:
  - Secret утёк в этот раз — меняем
  - Refresh token может истекать, прод остаётся без доступа

### Вариант B — App Password (рекомендую)
- В Google Account включаем 2FA
- Генерим App Password для почты
- Храним в env: `GMAIL_USER`, `GMAIL_APP_PASSWORD`
- Работаем через IMAP: `imaplib` в стандартной либе

**Плюсы:** проще, надёжнее, меньше кода.
**Минусы:** ограничено только Gmail'ом (OAuth универсален).

### Вариант C — Dedicated email / SMTP → webhook
- Выделенный ящик только для алертов VNNOX
- Через forwarding → свой SMTP → парсим напрямую
- Сложнее, но удобнее в долгосрочной

**Рекомендация:** переходим на Вариант B (IMAP + app password). OAuth оставляем в коде как устаревший путь, потом убираем.

---

## Архитектура (целевая)

```
apps/integrations/gmail/
├── client.py          — IMAP-клиент
├── parser.py          — парсер писем VNNOX
├── service.py         — фетч + создание AlarmEvent
├── management/commands/
│   └── poll_gmail.py  — запуск по cron
```

```python
class GmailClient:
    def __init__(self, settings):
        self._imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        self._imap.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)

    def fetch_unread(self, folder="INBOX", since: datetime | None = None) -> Iterator[RawMessage]:
        self._imap.select(folder)
        query = "UNSEEN"
        if since:
            query += f' SINCE "{since.strftime("%d-%b-%Y")}"'
        _, data = self._imap.search(None, query)
        for num in data[0].split():
            _, msg_data = self._imap.fetch(num, "(RFC822)")
            yield RawMessage.parse(msg_data[0][1])

    def mark_read(self, msg_id: str): ...
```

```python
class VnnoxAlarmParser:
    SUBJECT_PATTERN = re.compile(r"...")

    def parse(self, raw: RawMessage) -> Alarm | None:
        if not self.SUBJECT_PATTERN.match(raw.subject):
            return None
        # extract display name, panel id, event type, time
        ...
```

```python
class AlarmIngestService:
    def ingest(self):
        for raw in self._client.fetch_unread():
            if self._alarm_repo.exists(message_id=raw.message_id):
                continue
            try:
                alarm = self._parser.parse(raw)
            except Exception as e:
                logger.error("parse_failed", message_id=raw.message_id, exc=e)
                self._alarm_repo.save_as_parse_failed(raw, reason=str(e))
                continue
            
            if alarm is None:
                self._client.mark_read(raw.message_id)
                continue

            display = self._match_display(alarm)
            # Не создаём Application автоматически: мониторщик решает вручную в UI.
            
            self._alarm_repo.save(alarm)
            self._client.mark_read(raw.message_id)
```

---

## Мэппинг "Alarm → Display/Panel"

Какие поля у нас есть от VNNOX:
- `display name` (строкой, наш `Display.description` или `Display.name`)
- `pixel_position` или similar (mapping на `Cell.row/col`?)
- `error_code`
- `time`

**Вопрос к владельцу:** уточнить формат письма — скинуть пример пары-тройки писем, чтобы написать парсер точно.

---

## Миграция с OAuth

1. Написать новый клиент (App Password)
2. В settings — включаемый flag `GMAIL_AUTH_METHOD = 'app_password' | 'oauth'`
3. Параллельно работают обе, переключение по env
4. Через неделю — удалить OAuth код

---

## Secrets

```env
GMAIL_USER=alarm-receiver@mstechnics.ru
GMAIL_APP_PASSWORD=***
GMAIL_FOLDER=INBOX
GMAIL_POLL_INTERVAL_MIN=15
```

Существующие файлы:
- `Config/client_secret.json` → удалить, в `.gitignore`
- `Config/token.pickle` → удалить
- Секрет, который утёк (`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`) — **отозвать в Google Cloud Console**

---

## Развёртывание

Management command + systemd timer:
```ini
# /etc/systemd/system/mstechnics-gmail-poll.service
[Unit]
Description=MsTechnics Gmail Alarm Poller
[Service]
WorkingDirectory=/app/mstechnics
ExecStart=/usr/bin/python manage.py poll_gmail
User=mstechnics
EnvironmentFile=/etc/mstechnics/env

# /etc/systemd/system/mstechnics-gmail-poll.timer
[Unit]
Description=Run gmail poll every 15 minutes
[Timer]
OnCalendar=*:0/15
Persistent=true
[Install]
WantedBy=timers.target
```

Или Docker — тот же timer в Docker Swarm / k8s CronJob.

---

## Тесты

- Unit: парсер на 10+ фикстурах писем
- Integration: mock IMAP-сервер, проверка flow
- Manual: раз в месяц скидываем реальный тест и проверяем

---

## Что блокирует эту задачу

Нужны примеры реальных писем от VNNOX (можно anonymized). Пусть владелец пришлёт 5-10 штук в виде `.eml`.
