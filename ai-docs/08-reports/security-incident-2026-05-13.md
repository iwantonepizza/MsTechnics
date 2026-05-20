# Security Incident 2026-05-13

> **Приоритет:** P0
> **Автор:** GPT-5 Codex + владелец
> **Дата обнаружения:** 2026-05-13
> **Связанные задачи:** `T-6-004`, `T-6-005`

---

## Что произошло

В git-истории репозитория были обнаружены и ранее pushed в `origin` чувствительные артефакты:

- `Config/.env`
- `Config/client_secret.json`
- prod dump (`mstechnics.dump`, `db_dumps/`)
- служебные логи прогонов и связанные артефакты

По состоянию на `2026-05-13` история уже очищена и force-pushed в рамках `T-6-004`, но это не инвалидирует секреты, которые могли быть извлечены из старых клонов или mirror-копий.

---

## Что было скомпрометировано

Минимальный список на проверку / отзыв:

- `SECRET_KEY`
- `DATABASE_PASSWORD`
- `TELEGRAM_BOT_TOKEN`
- `MAX_BOT_TOKEN`
- `MAX_WEBHOOK_SECRET`
- `SENTRY_DSN`
- Google OAuth client credentials (`Config/client_secret.json`)
- Gmail OAuth refresh/access token (`Config/token.pickle`) как зависимый артефакт, подлежащий перевыпуску после замены client id

---

## Таймлайн

- `2026-05-13`: обнаружено, что в истории были tracked `Config/.env` и `Config/client_secret.json` вместе с prod-дампами и логами.
- `2026-05-13`: выполнен `T-6-004` — `.gitignore` усилен, история переписана через `git-filter-repo`, выполнен force-push.
- `2026-05-13`: открыт `T-6-005` на ротацию всех потенциально утёкших секретов.

Commit SHA исходной утечки и точные даты первоначального push нужно при возможности восстановить владельцем отдельно, если это важно для внешнего incident log.

---

## Ротация секретов

| Секрет / артефакт | Статус | Дата ротации | Комментарий |
|---|---|---|---|
| `SECRET_KEY` | pending owner | — | Требует перезапуск web |
| `DATABASE_PASSWORD` | pending owner | — | Требует ALTER USER + обновление `.env` |
| `TELEGRAM_BOT_TOKEN` | pending owner | — | BotFather `/revoke` |
| `MAX_BOT_TOKEN` | pending owner | — | Reset token в dev.max.ru |
| `MAX_WEBHOOK_SECRET` | pending owner | — | Перегенерировать 32+ random chars |
| `SENTRY_DSN` | optional / pending owner | — | Только если реально был выставлен |
| Google OAuth `client_secret.json` | pending owner | — | Старый OAuth Client ID удалить |
| Gmail `token.pickle` | pending owner | — | Удалить и перевыпустить после нового client id |

---

## Решение по пользовательским паролям

Pending owner decision.

Базовая оценка риска:

- в прод-дампе присутствуют Django password hashes (`pbkdf2_sha256$...`);
- это не plain-text, но при слабых паролях возможен offline cracking;
- если репозиторий или его копии были доступны шире, чем владелец + кодер, разумно провести forced reset.

---

## Lessons Learned

- `.env`, `client_secret.json`, `token.pickle`, дампы БД и operational logs никогда не должны быть tracked.
- Force-push лечит историю remote, но не лечит уже утёкшие секреты; после любой такой утечки обязателен отзыв / перевыпуск.
- `.env.example` должен содержать только явные placeholders, а не bootstrap-строки, похожие на реальные секреты.

---

## Следующие действия

- Владелец выполняет шаги ротации из `T-6-005`.
- После завершения owner-side действий этот incident report обновляется фактическими датами ротации и итоговым решением по password reset.
