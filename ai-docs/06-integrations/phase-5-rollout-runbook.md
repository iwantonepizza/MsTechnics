# Phase 5 rollout runbook

Дата: 2026-05-05

Цель: включить новые уведомления и VNNOX-алармы на staging/prod после снятия блока T-5-011. В этой ветке legacy `sender_tg_message.py`/`tg_sender` уже удалены; старый прод остаётся на старой версии до отдельного выката.

---

## 1. Env на prod/staging

Добавить или проверить в real env. Секреты не коммитить.

```bash
# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_PROXY_URL=socks5://user:password@host:1080
TELEGRAM_TIMEOUT_SEC=30

# MAX
MAX_BOT_TOKEN=...
MAX_API_BASE=https://platform-api.max.ru
MAX_WEBHOOK_SECRET=...
MAX_TIMEOUT_SEC=30

# Email fallback
DEFAULT_FROM_EMAIL=noreply@mstechnics.local

# VNNOX
VNNOX_ALARM_NOTIFY_THRESHOLD_MINUTES=15
```

Legacy env `TOKEN=...` больше не используется новой веткой. На старом проде его можно оставить до переключения версии.

---

## 2. Миграции

Перед применением на prod обязательно прогнать на копии БД:

```bash
python manage.py migrate --plan
python manage.py migrate
```

Ожидаемые новые миграции:

- `directory_displays.0002_display_vnnox_device_id`
- `gmail_alarms.0001_initial`
- `notifications.0003_vnnox_alarm_template`
- `notifications.0004_legacy_message_template`

Если всплывает `KeyError: 'display'` или legacy duplicate model errors — сначала чинить migration graph, не катить prod.

---

## 3. Telegram proxy smoke

```bash
python scripts/check_telegram_proxy.py
```

Успех:

```json
{"ok": true, "proxy": "socks5://user:***@host:1080", "telegram_user": "..."}
```

Если падает:

- проверить `TELEGRAM_BOT_TOKEN`;
- проверить `TELEGRAM_PROXY_URL`;
- проверить firewall/VPS/3proxy;
- держать старый prod на старой версии до исправления proxy/env.

---

## 4. MAX webhook smoke

После регистрации webhook у MAX:

```text
POST https://mstechnics.ru/api/v1/integrations/max/webhook
Header: X-MAX-Secret: <MAX_WEBHOOK_SECRET>
```

Проверки вручную:

- пользователь пишет боту `/start <username>`;
- в БД у `MsUser` заполняется `max_id`;
- `/unbind` очищает `max_id`;
- тестовое уведомление доставляется через `MaxChannel`;
- callback `application_done:<id>` работает только на валидной заявке и валидном переходе.

---

## 5. VNNOX smoke

Перед запуском:

- заполнить `Display.vnnox_device_id` для экранов в admin;
- убедиться, что Gmail OAuth token доступен как `Config/token.pickle`.
- На production 2026-06-05 `Config/token.pickle` отсутствует и `Display.vnnox_device_id` заполнен у `0/8` экранов, поэтому `mstechnics-vnnox-pull.timer` нельзя включать до заполнения этих данных.

Команды:

```bash
python manage.py pull_vnnox_alarms --no-mark-read
python manage.py check_unresolved_alarms --threshold-minutes 15
```

После dry-run:

```bash
python manage.py pull_vnnox_alarms
```

Проверки:

- создаются `AlarmEvent`;
- recovery закрывает открытый faulty;
- DisplayView показывает вкладку `VNNOX`;
- кнопка «Создать заявку» открывает форму с prefill-комментарием;
- заявки автоматически не создаются.

---

## 6. Timers

На Linux host:

```bash
sudo cp infra/systemd/mstechnics-daily-tasks.* /etc/systemd/system/
sudo cp infra/systemd/mstechnics-vnnox-pull.* /etc/systemd/system/
sudo cp infra/systemd/mstechnics-vnnox-unresolved.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mstechnics-daily-tasks.timer
sudo systemctl enable --now mstechnics-vnnox-pull.timer
sudo systemctl enable --now mstechnics-vnnox-unresolved.timer
systemctl list-timers 'mstechnics-*'
```

Production unit-файлы в repo актуализированы под `/root/DisplayControl/MsTechnics` и `/root/DisplayControl/venv-c84d3816`. Если venv или checkout меняются, заменить `WorkingDirectory`, `EnvironmentFile`, `ExecStart` перед `systemctl daemon-reload`.

---

## 7. Post-cutover soak

После выката ветки без `sender_tg_message.py` и `tg_sender` наблюдать 24 часа:

- новые notification triggers создают уведомления;
- Telegram через proxy доставляет;
- MAX fallback доставляет при недоступном TG;
- нет дублей уведомлений;
- нет ошибок в logs по `notification_all_channels_failed`.

Что уже сделано в T-5-011:

- `sender_tg_message.py` удалён;
- `tg_sender` удалён из `docker-compose.yml`;
- `sorting_message.py` оставлен как compat shim, потому его ещё импортируют `application`, `zip`, `main`.

Следующий cleanup:

- удалить `sorting_message.py`, когда legacy imports исчезнут в T-5-050;
- удалить legacy env `TOKEN` после переключения prod на новую ветку.

---

## 8. Что не делать

- Не класть реальные токены в git.
- Не переключать prod на новую ветку, пока `TELEGRAM_BOT_TOKEN`/`TELEGRAM_PROXY_URL`/`MAX_*` не проверены.
- Не запускать legacy cleanup `T-5-050` до staging/prod SPA stability window.
- Не создавать заявки из VNNOX автоматически.
