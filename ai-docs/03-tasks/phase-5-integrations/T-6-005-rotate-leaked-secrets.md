# T-6-005. Ротация утёкших секретов после T-6-004

> **Тип задачи:** security (post-incident)
> **Приоритет:** P0 (история репо переписана, но старые секреты валидны до отзыва)
> **Оценка:** 1-2 часа (зависит от того, сколько секретов реально утекло)
> **Фаза:** 6 (production)
> **Статус:** review
> **Исполнитель:** **владелец** + GPT-5 Codex (кодер; owner-only шаги остаются у владельца: доступ к Google Cloud Console, BotFather, dev.max.ru, прод-БД)

---

## Цель

После T-6-004 история git очищена и force-pushed, но **секреты, которые были в `Config/.env` и `Config/client_secret.json`, считаются скомпрометированными**. Любой, кто клонировал репо ДО force-push, и любой, у кого есть git mirror, всё ещё может извлечь старые секреты. Force-push на remote это не лечит — лечит только **отзыв и выпуск новых**.

---

## Контекст

Из отчёта T-6-004:

> Утечка была не только по прод-дампу и логам, но и по tracked `Config/.env` и `Config/client_secret.json`. Чувствительные артефакты уже были pushed в GitHub remote `origin`.

Что **могло** быть в этих файлах (нужно проверить владельцем):

| Файл | Что внутри (типично) |
|---|---|
| `Config/.env` | `SECRET_KEY`, `DATABASE_PASSWORD`, `TELEGRAM_BOT_TOKEN`, `MAX_BOT_TOKEN`, `MAX_WEBHOOK_SECRET`, `SENTRY_DSN`, и т.д. |
| `Config/client_secret.json` | Полные OAuth credentials для Google API (для VNNOX Gmail парсера): `client_id`, `client_secret`, `redirect_uris` |

Без ротации:
- Любой, у кого есть копия `client_secret.json`, может выпустить OAuth-токен и читать Gmail VNNOX-почту.
- Скомпрометированный `SECRET_KEY` ломает целостность Django session/JWT — теоретически можно подделать токены.
- TG/MAX bot tokens — атакующий может отправлять сообщения от имени бота.

---

## Зависимости

- **Блокируется:** T-6-004 done (история переписана). ✅
- **Блокирует:** prod cutover (T-6-001) — потому что на prod нужны **новые** реальные секреты в .env, и старый `client_secret.json` не должен использоваться.

---

## Что нужно сделать

### Шаг 1. Инвентаризация (владелец)

Открыть `.env.example` и пройтись по списку — какие из этих переменных были выставлены реально в утёкшем `Config/.env`. Каждая выставленная = скомпрометирована.

Минимальный чек-лист:

- [ ] `SECRET_KEY`
- [ ] `DATABASE_PASSWORD`
- [ ] `TELEGRAM_BOT_TOKEN`
- [ ] `MAX_BOT_TOKEN`
- [ ] `MAX_WEBHOOK_SECRET`
- [ ] `SENTRY_DSN`
- [ ] `Config/client_secret.json` (Google OAuth) — **был файл, не env-переменная, но та же утечка**

### Шаг 2. Ротация Google OAuth credentials (владелец, ~10 мин)

Это **самое критичное**, потому что Gmail VNNOX-парсер работает от имени конкретного Google account.

1. Открыть https://console.cloud.google.com/apis/credentials
2. Найти OAuth 2.0 Client ID, который соответствует утёкшему `client_secret.json`.
3. Нажать **«Delete»** на старом client ID.
4. Создать новый OAuth 2.0 Client ID того же типа (Desktop App / Web Application).
5. Скачать новый `client_secret.json`.
6. Положить на сервер в `Config/client_secret.json` (НЕ коммитить).
7. Удалить старый `Config/token.pickle` на сервере (потому что он был выписан старому client_id).
8. Перевыполнить OAuth flow с новым client_id, получить новый `token.pickle`.

Проверка: `python scripts/check_telegram_proxy.py`-style — добавить аналогичный `scripts/check_gmail_oauth.py` (тестовый запрос `users.messages.list` от Gmail API). Без неё — увидим только при первом прогоне `pull_vnnox_alarms`.

### Шаг 3. Ротация Django `SECRET_KEY` (владелец, ~2 мин)

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Положить в `Config/.env` на сервере как новый `SECRET_KEY`. После перезапуска web — все существующие Django session cookies инвалидируются (пользователи переавторизуются). JWT-токены валидны до своего TTL — это окей.

### Шаг 4. Ротация `DATABASE_PASSWORD` (владелец, ~5 мин)

```sql
-- На прод-БД, под суперюзером
ALTER USER mstechnics WITH PASSWORD '<новый_пароль>';
```

Затем в `Config/.env` сервера обновить `DATABASE_PASSWORD`. Перезапустить web + воркеры.

### Шаг 5. Ротация TG bot token (владелец, ~3 мин)

В Telegram написать `@BotFather`, выбрать бота → `/revoke` → выпустить новый токен. Обновить `TELEGRAM_BOT_TOKEN` в `Config/.env`. Перезапустить notification dispatcher.

### Шаг 6. Ротация MAX bot token (владелец, ~5 мин)

Зайти на https://dev.max.ru, найти бота → "Reset token". Обновить `MAX_BOT_TOKEN` в `Config/.env`. Также — **`MAX_WEBHOOK_SECRET`** перегенерить (любая случайная строка 32+ символов, `python -c "import secrets; print(secrets.token_urlsafe(32))"`). После обновления — заново зарегистрировать webhook у MAX.

### Шаг 7. Ротация Sentry DSN (опционально, ~5 мин)

В https://sentry.io проекта → Settings → Client Keys (DSN) → "Generate new" / "Revoke old". Обновить `SENTRY_DSN` в `Config/.env`. Старые ошибки в Sentry остаются доступны для чтения; новые приходят через новый DSN.

### Шаг 8. Решение по паролям пользователей (владелец)

В прод-БД 7 пользователей, их хеши паролей (`pbkdf2_sha256$...`) утекли. Хеши не plain-text, но при слабом пароле — `hashcat`/`john` за разумное время сломает.

**Решение архитектора:** если **репо приватный** и доступ был только у владельца + кодеров — пропустить. Если был хотя бы один публичный момент (форк, GitHub mirror, или старая копия у кого-то ушла) — провести reset.

Procedure если делаем reset:

```python
# Django shell на сервере
from django.contrib.auth import get_user_model
User = get_user_model()
for u in User.objects.all():
    u.set_unusable_password()
    u.save()
```

И уведомить пользователей: «Из-за инцидента безопасности после следующего входа нужно сбросить пароль через `/admin/password_reset/`».

### Шаг 9. Документация инцидента

Создать `ai-docs/08-reports/security-incident-2026-05-13.md` с фактами:

- Дата обнаружения утечки.
- Что утекло.
- Когда было запушено (commit SHA если знаем).
- Когда история переписана (T-6-004 done date).
- Список ротированных секретов с датой ротации.
- Решение по паролям пользователей.
- Lessons learned: после этого `.env` и `client_secret.json` строго в `.gitignore`, никогда не tracked.

### Шаг 10. Проверка

После всех ротаций:

```bash
# На сервере
.venv/bin/python scripts/check_telegram_proxy.py     # с новым TG token
.venv/bin/python manage.py pull_vnnox_alarms --dry-run   # с новым Google OAuth
# проверка JWT
curl -sX POST $HOST/api/v1/auth/login/ -d '...' | jq .access
```

Все три должны работать. Если падает — конкретный секрет не ротирован/неправильно записан.

---

## Критерии приёмки

- [ ] Чек-лист по 6 секретам (Шаг 1) проставлен — что было реально выставлено, что нет.
- [ ] Google OAuth credentials ротированы (новый `client_secret.json` + новый `token.pickle`).
- [ ] `SECRET_KEY` Django ротирован.
- [ ] `DATABASE_PASSWORD` ротирован (или явно отмечено «не было выставлено, дефолт `change_me`»).
- [ ] `TELEGRAM_BOT_TOKEN` ротирован (или «не было выставлено»).
- [ ] `MAX_BOT_TOKEN` + `MAX_WEBHOOK_SECRET` ротированы (или «не было выставлено»).
- [ ] Решение по паролям пользователей принято и зафиксировано.
- [ ] `ai-docs/08-reports/security-incident-2026-05-13.md` написан.
- [ ] Отчёт в `ai-docs/08-reports/T-6-005.md`.

---

## Что НЕ нужно делать

- **Не публиковать новые секреты в чате/issues/PR.** Любые обмены — через password manager, защищённый канал, или прямой ввод на сервере владельцем.
- **Не сидеть на старом `token.pickle`** «до следующей ошибки». Он точно скомпрометирован.
- **Не ротировать всё подряд** «на всякий случай». По чек-листу — что было выставлено, то и ротируем.

---

## Отчёт

### Что сделано кодером

- Добавлен `scripts/check_gmail_oauth.py` для безопасной проверки Gmail OAuth через тестовый `users.messages.list`.
- В `apps/integrations/gmail_alarms/services.py` вынесен reusable helper `check_gmail_oauth(...)` с проверкой наличия `client_secret.json` и `token.pickle`.
- `.env.example` очищен от bootstrap-значений с видом реальных секретов; оставлены явные placeholder-значения.
- Созданы отчёты `ai-docs/08-reports/T-6-005.md` и `ai-docs/08-reports/security-incident-2026-05-13.md`.

### Что остаётся владельцу

- Выполнить owner-only шаги 1-8 и 10: inventory, ротацию Google OAuth / Django `SECRET_KEY` / БД / TG / MAX / optional Sentry.
- После фактической ротации обновить incident report датами и финальным списком реально отозванных секретов.
