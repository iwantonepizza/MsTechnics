# T-4-002-followup. Добивка OpenAPI генерации

> **PR:** N/A
> **Автор:** GPT-5 Codex
> **Дата:** 2026-05-05
> **Статус задачи в 03-tasks/:** review

---

## Что сделано

- ✅ Сгенерирован `api-schema.yaml` в корне проекта.
- ✅ Сгенерирован `frontend/src/shared/api/schema.d.ts` через `openapi-typescript`.
- ✅ `frontend/src/shared/api/types.ts` переписан на алиасы из `schema.d.ts`.
- ✅ Исправлены startup-блокеры, которые мешали генерации схемы: settings-модуль, конфликт legacy/new user app, битые импорты и некорректные serializer fields.
- ✅ Добавлены `@extend_schema_field` для ключевых `SerializerMethodField`, чтобы generated TS-типы не деградировали в `string`.
- ✅ `npm run typecheck` проходит.

---

## Отклонения от плана

- **Что:** команда генерации схемы выполнялась как `python manage.py spectacular --skip-checks --validate --file api-schema.yaml`.
- **Почему:** текущий transitional state проекта одновременно содержит legacy и new apps с одинаковыми `db_table`, из-за чего Django system checks падают на известных дублях моделей. OpenAPI-генерация при этом валидна и проходит `--validate`.
- **Нужно ли обновить архитектурный документ:** нет, это уже отражено в фазовом рефакторинге legacy/new слоёв.

---

## Архитектурные решения

- `manage.py`, `Config/asgi.py`, `Config/wsgi.py`, `pyproject.toml` переведены на фактический settings-пакет `Config.settings`, иначе `drf-spectacular` не регистрируется.
- Legacy app `user` убран из `Config.settings`, потому что `apps.core.users` сохраняет label `user` для `AUTH_USER_MODEL = "user.MsUser"`.
- `types.ts` оставлен thin wrapper над generated schema, но с локальным усилением типов для полей, которые UI использует как обязательные (`DisplayDetail.rows/cols/cells`, `DisplayListItem.slug`).

---

## Тесты

- Новых файлов с тестами: 0
- Добавлено тестов: 0
- Coverage нового кода: N/A
- Что покрыто:
  - `python manage.py spectacular --skip-checks --validate --file api-schema.yaml`
  - `npm run generate:api-types`
  - `npm run typecheck`
- Что НЕ покрыто и почему:
  - Backend pytest не запускался: задача инфраструктурная, локальная БД не поднималась.

---

## Нагрузка / производительность

N/A

---

## Миграции

N/A

---

## Время

- Оценка в задаче: 0.5 часа
- Фактически: около 1.5 часа
- Причина превышения: генерация выявила несколько накопленных startup/schema/typecheck блокеров, не описанных в карточке.

---

## Проверки перед PR

- [x] `python manage.py spectacular --skip-checks --validate --file api-schema.yaml` — зелёное, schema файл создан
- [x] `npm run generate:api-types` — зелёное
- [x] `npm run typecheck` — зелёное
- [ ] `pytest` — не запускался, нужна локальная БД
- [ ] `mypy` — не запускался
- [x] Нет debug-кода
- [x] Нет секретов

---

## Скриншоты / демо

N/A

---

## Дальнейшие шаги

- Убрать `--skip-checks`, когда legacy apps будут исключены из `INSTALLED_APPS` или полностью вычищены.
- Почистить оставшиеся drf-spectacular warnings/errors: path parameter typing, duplicate component names `Cell`/`ExecutorMini`, schema для `health` и `dashboard` APIView.
- Привести frontend package manager к одному стандарту: карточка ожидает `pnpm`, но локально был доступен только `npm`.

---

## Вопросы архитектору / ретро

- Нужно ли в T-4-040 отдельно завести CI-проверку, которая сравнивает `api-schema.yaml` после генерации и падает на diff.
