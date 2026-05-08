# T-4-002-followup. Добивка OpenAPI генерации

> **Тип:** infra / cleanup
> **Приоритет:** P0
> **Оценка:** 30 минут
> **Фаза:** 4
> **Статус:** review
> **Взял:** GPT-5 Codex

---

## Цель

Дожать T-4-002 до конца. Уже сделано:

- ✅ `Makefile` создан с командами `api-schema`, `fe-types`
- ✅ `frontend/package.json` содержит script `generate:api-types`
- ✅ `drf-spectacular` настроен в `config/settings.py`

Не сделано:

- ❌ `api-schema.yaml` в корне проекта **не сгенерирован** (нет файла)
- ❌ `frontend/src/shared/api/schema.d.ts` **не существует**
- ❌ `frontend/src/shared/api/types.ts` всё ещё **ручной** (25 строк)

Без этого фронт пишет типы вручную и они расходятся со схемой.

---

## Что сделать

### Шаг 1. Сгенерировать схему

```bash
cd /path/to/MsTechnics
make api-schema
```

Команда из Makefile:
```makefile
api-schema:
	python manage.py spectacular --validate --file api-schema.yaml
```

Результат: файл `api-schema.yaml` в корне (~50-200 KB в зависимости от количества endpoints).

**Если падает с ошибкой** — задокументируй ошибку в отчёте + исправь schema warnings (обычно missing `serializer_class` в каком-то ViewSet).

### Шаг 2. Сгенерировать TS-типы

```bash
make fe-types
```

Команда:
```makefile
fe-types: api-schema
	cd frontend && pnpm run generate:api-types
```

В `package.json`:
```json
"generate:api-types": "openapi-typescript ../api-schema.yaml -o src/shared/api/schema.d.ts"
```

Результат: `frontend/src/shared/api/schema.d.ts` (несколько сот строк, генерируется).

### Шаг 3. Переписать `types.ts` через алиасы

Старый файл (`frontend/src/shared/api/types.ts`) — заменить на:

```ts
import type { components } from './schema.d'

export type Schemas = components['schemas']

// Удобные алиасы — короче чем Schemas['DisplayDetail']
export type City               = Schemas['City']
export type Color              = Schemas['Color']
export type Smile              = Schemas['Smile']
export type Condition          = Schemas['Condition']
export type Department         = Schemas['Department']
export type ApplicationStatus  = Schemas['ApplicationStatus']
export type DepartureStatus    = Schemas['DepartureStatus']
export type DisplayListItem    = Schemas['DisplayListItem']
export type DisplayDetail      = Schemas['DisplayDetail']
export type Cell               = Schemas['Cell']
export type Panel              = Schemas['Panel']
export type Application        = Schemas['Application']
export type ApplicationDetail  = Schemas['ApplicationDetail']
export type ApplicationEvent   = Schemas['ApplicationEvent']
export type Departure          = Schemas['Departure']
export type Executor           = Schemas['Executor']
export type Me                 = Schemas['MeUser']

// Не из схемы — наши хелперы
export interface PaginatedResponse<T> {
  results: T[]
  next_cursor: string | null
  prev_cursor: string | null
  has_more: boolean
}

export interface ApiError {
  detail: string
  code: string
  errors: Record<string, string[]> | null
}
```

**Важно:** имена в `Schemas[...]` должны совпадать с тем, что drf-spectacular сгенерировал. Если name в схеме `DisplayDetailSerializer` — алиас будет `Schemas['DisplayDetailSerializer']`. Проверить через `grep "components/schemas" api-schema.yaml | head`.

### Шаг 4. Тайпчек

```bash
cd frontend
pnpm typecheck
# должно пройти без ошибок
# если есть несовпадения типов в существующих компонентах — пофиксить
```

### Шаг 5. Коммит

```bash
git add api-schema.yaml frontend/src/shared/api/schema.d.ts frontend/src/shared/api/types.ts
git commit -m "T-4-002: generate OpenAPI schema, regenerate TS types

api-schema.yaml committed for fe-types reproducibility.
types.ts now imports from auto-generated schema.d.ts."
```

---

## Критерии приёмки

- [ ] `api-schema.yaml` существует в корне проекта (>10 KB)
- [ ] `python manage.py spectacular --validate` проходит
- [ ] `frontend/src/shared/api/schema.d.ts` существует и валидный TS
- [ ] `types.ts` импортирует через `import type { components } from './schema.d'`
- [ ] `pnpm typecheck` зелёный
- [ ] Commit включает все три файла

---

## Что НЕ делать

- НЕ редактировать `schema.d.ts` руками (генерируется)
- НЕ забыть `--validate` — отлавливает schema bugs
- НЕ удалять `api-schema.yaml` из репо — нужен для воспроизводимости генерации фронт-типов

---

## Workflow на будущее

При изменении API:

1. Backend кодер изменяет код
2. Прогоняет `make api-schema`
3. Коммит включает обновлённый `api-schema.yaml`
4. Frontend кодер: `make fe-types`
5. `schema.d.ts` обновляется
6. Адаптирует код под новые/изменённые типы

CI шаг (для T-4-040 потом):
```yaml
- run: make api-schema
- run: |
    if ! git diff --exit-code api-schema.yaml; then
      echo "❌ api-schema.yaml не синхронизирован — запустите make api-schema"
      exit 1
    fi
```

---

## Отчёт

После выполнения — отчёт `ai-docs/08-reports/T-4-002-followup.md` по шаблону:
- Сколько endpoints в схеме (`grep "operationId:" api-schema.yaml | wc -l`)
- Какие типы появились новые
- Сломалось ли что-то в существующем коде после регенерации (`pnpm typecheck`)
