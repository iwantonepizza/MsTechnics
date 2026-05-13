# T-6-004. .gitignore + проверка утечки прод-данных в git

> **Тип задачи:** security + hygiene
> **Приоритет:** P0 (security — прод-дамп с PII в git)
> **Оценка:** 30 минут — 2 часа (зависит от того, утекло ли в публичный remote)
> **Фаза:** 6 (production)
> **Статус:** in-progress
> **Исполнитель:** GPT-5 Codex

---

## Цель

Сейчас в репо лежат файлы, которые не должны быть в git:
- `mstechnics.dump` (в корне) — прод-дамп с реальными именами/комментариями/исполнителями.
- `db_dumps/mstechnics.dump` — то же.
- `logs/t5_fix_003_*` — 17 файлов с артефактами прогона миграций; в `schema_clean.sql`/`schema_prod_after.sql` содержатся имена таблиц и индексов, в `smoke_login.txt`/`smoke_displays_body.json` могут быть JWT и данные пользователей.
- `mstechnics.egg-info/` — артефакт editable install.
- `staticfiles/` — собранные статики (если есть).

Цель — закрыть `.gitignore`, проверить историю на утечку и (при необходимости) почистить.

---

## Контекст

`db_dumps/mstechnics.dump` — это **прод-дамп с реальными данными**. 7 пользователей с реальными username (= ФИО или ник), 8 экранов с реальными названиями и координатами камер, 2333 панели с реальными комментариями обслуживания, 10 заявок с реальными комментариями исполнителей.

Это PII по нашей конвенции:
- `ai-docs/01-current-state/security-issues.md` — `SEC-001..004` про коммит секретов.
- `AGENTS.md`, раздел «Что строго запрещено», п. 1: «НЕ коммитить .env, client_secret.json, token.pickle, любые ключи».

Дамп подпадает под этот же принцип. Если репо public/shared — это leak.

---

## Зависимости

- **Блокируется:** ничем (можно брать сейчас, должно быть до prod-cutover).
- **Блокирует:** ничего, но публичный remote — это критичный security gate.

---

## Что нужно сделать

### Шаг 1. Проверить, утекло ли уже

```bash
# Локально
git log --all --full-history -- "*.dump" "db_dumps/*" "logs/*" "mstechnics.egg-info"
```

**Если нет коммитов** с этими путями — это локальные untracked файлы. Просто фиксим `.gitignore`.

**Если коммиты есть:**

```bash
git ls-tree -r HEAD -- "db_dumps/" "*.dump" "logs/"
```

— показывает, что **сейчас в HEAD**. Если файлы в актуальном HEAD:

```bash
# Узнать remote и был ли push
git remote -v
git log origin/main --oneline -20
```

Если push в публичный remote был — это **полноценная утечка**, требует `git filter-repo` + force push + смену всех ротируемых secrets (но в дампе нет токенов API — только PII).

### Шаг 2. Обновить `.gitignore`

Добавить в `.gitignore`:

```
# DB dumps — никогда в git
*.dump
*.sql.gz
dumps/
db_dumps/

# Logs и временные артефакты прогонов
logs/
*.log
!*.example.log

# Python build artefacts
*.egg-info/
__pycache__/
*.pyc

# Django collected static (re-collect on deploy)
staticfiles/

# Local env
.env
.env.local
Config/.env
Config/token.pickle
Config/client_secret.json

# Test artefacts
.coverage
.coverage.*
htmlcov/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# IDE
.vscode/
.idea/
*.swp
```

### Шаг 3. Удалить файлы из tracked, если они там

```bash
git rm --cached -r db_dumps/ mstechnics.dump logs/ mstechnics.egg-info/ staticfiles/ 2>/dev/null || true
git status
```

Затем коммит:

```bash
git add .gitignore
git commit -m "T-6-004: gitignore prod dumps, logs, build artefacts"
```

### Шаг 4. Если файлы попадали в публичный remote — почистить историю

```bash
pip install git-filter-repo

git filter-repo \
  --path-glob '*.dump' \
  --path db_dumps \
  --path logs \
  --path mstechnics.egg-info \
  --invert-paths
```

**Внимание**: `git filter-repo` переписывает историю. Все клоны репо должны быть пересозданы с нуля. Это согласовывается с владельцем заранее.

После — force push:

```bash
git push --force origin main
```

И сообщить владельцу: если репо был форкнут или клонирован кем-то ещё (даже внутри команды) — те копии тоже надо удалить, потому что дамп в git history останется.

### Шаг 5. Сменить (если надо) пароли пользователей в проде

В дампе — Django auth hashes (`pbkdf2_sha256$…`). По хорошему это хеши, не plain-text, но если репо публичный — стандартная процедура: попросить всех пользователей сменить пароли после prod-cutover (`User.objects.update(password='')` + force reset на следующий login).

Решение по этому шагу — за владельцем. Если репо приватный и доступ только у двух-трёх человек — можно не дёргать.

### Шаг 6. Документация

В `ai-docs/04-conventions/security-conventions.md` добавить раздел «Что не коммитим»:

- Дампы БД (любого размера).
- Логи прогонов.
- `.env`, `client_secret.json`, `token.pickle`.
- Build artefacts.

---

## Критерии приёмки

- [ ] `.gitignore` обновлён.
- [ ] `git status` не показывает untracked dumps/logs/egg-info.
- [ ] `git log --all -- "*.dump"` показывает либо ничего (новый репо), либо точно ясно, нужен ли `filter-repo`.
- [ ] Если был push — история почищена через `git filter-repo` + force push.
- [ ] `04-conventions/security-conventions.md` написан/обновлён.
- [ ] Отчёт в `08-reports/T-6-004.md`.

---

## Что НЕ нужно делать

- **Не делать `git filter-repo` без согласования с владельцем.** Force push ломает все клоны.
- **Не удалять `db_dumps/mstechnics.dump` физически** с диска — он нужен для тестирования cutover (T-6-001). Только из git.
- Не публиковать дамп в облако с публичным доступом для удобства.

---

## Отчёт

(Заполняет кодер.)
