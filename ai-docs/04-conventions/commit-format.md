# Commit Format

Conventional Commits + task ID.

## Формат

```
<type>(<scope>): <subject>

<body>

<footer>
```

## Типы (type)

| Type | Когда |
|---|---|
| `feat` | новый функционал для пользователя |
| `fix` | исправление бага |
| `refactor` | изменение кода без изменения поведения |
| `perf` | улучшение производительности |
| `test` | добавление/правка тестов |
| `docs` | только документация (README, ai-docs/) |
| `chore` | зависимости, конфиги, infra |
| `style` | форматирование (ruff, black) — без функциональных правок |
| `ci` | изменения CI |
| `revert` | откат коммита |

## Scope

Название затронутого приложения или компонента:
- `auth`, `applications`, `panels`, `notifications`, `api`, `admin`
- Или `frontend`, `infra`, `tests`

## Subject

- **Русский или английский, консистентно** (лучше русский, т.к. commit history — для команды)
- < 72 символа
- Без точки в конце
- Повелительное наклонение: «добавь», «убери», «переименуй» (не «добавил»)

## Body

Опциональный. Отделён пустой строкой от subject.
- Что и зачем меняли (не как — это видно в diff)
- Ограничивай строки 80 символов
- Можно списком через `- `

## Footer

- `Refs: T-1-007` — ссылка на задачу
- `Closes: T-1-007` — закрывает задачу полностью
- `BREAKING CHANGE: <описание>` — ломающее изменение
- `Co-authored-by: Name <email>` — если парно писали

## Примеры

### Простой фикс
```
fix(applications): не падать при удалении заявки без комментария

Refs: T-1-006
```

### Фича с деталями
```
feat(notifications): добавить MAX как канал уведомлений

- MaxChannel реализует NotificationChannel Protocol
- Добавлено поле MsUser.max_chat_id с миграцией
- /bind flow через webhook
- Настройки MAX_BOT_TOKEN, MAX_WEBHOOK_TOKEN вынесены в .env

Тесты: unit для парсера update-ов, integration с httpx-mock.
Webhook'и настраивать management-командой setup_max_webhook.

Closes: T-5-020, T-5-021
Refs: user-task-13
```

### Breaking change
```
refactor(applications): перенести FSM из utils.py в ApplicationStateMachine

BREAKING CHANGE: signature apply_application(id, comment, request) заменена
на transition_application(application_id, target_state, user, *, comment=None).
Старую функцию помечаем DeprecationWarning, удалим в следующем релизе.

Closes: T-2-010
```

### Hotfix
```
fix(infra): отозвать скомпрометированный Google OAuth secret

- Config/client_secret.json убран из репо
- История очищена через git-filter-repo
- Новый secret в .env только

Incident: ai-docs/08-reports/incident-2025-MM-DD-google-secret-leak.md
Closes: SEC-001
```

## Правила

- **Один коммит — одна логическая единица изменений.**
- **Не смешивай refactor + feature** в одном коммите.
- **`chore: WIP`** — запрещено в main. Допустимо на своей ветке во время работы, перед PR — сквашни.
- **Автокоммитов от IDE** не должно быть.

## Как сквошить перед PR

```bash
# посмотреть последние N коммитов
git log --oneline -20

# интерактивный rebase
git rebase -i HEAD~7

# в редакторе: поменять pick на squash/fixup где надо, сохранить
# потом редактор сообщения — оставить итоговое сообщение

# форс-пуш
git push --force-with-lease
```

## CI проверяет

- Формат коммита по regex (через `commitlint`)
- Наличие `Refs:` или `Closes:` с task-id (не блокирует мёрж, но warning в PR)
- Линтеры на diff
- Тесты
