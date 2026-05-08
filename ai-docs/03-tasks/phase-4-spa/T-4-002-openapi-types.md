# T-4-002. Генерация TS-типов из OpenAPI

> **Тип:** infra
> **Приоритет:** P0
> **Оценка:** 1.5 часа
> **Фаза:** 4
> **Статус:** review
> **Взял:** GPT-5 Codex

---

## Цель

Заменить ручной `frontend/src/shared/api/types.ts` (25 строк, 1:1 синхронизированы вручную) на автогенерируемые типы из `api-schema.yaml`. Это избавит от расхождений API↔frontend.

---

## Зависимости

- **Блокируется:** T-3-fix-001 (схема корректна)
- **Блокирует:** T-4-013..016 (страницы используют типы)

---

## Что сделать

### Шаг 1. Backend — экспорт схемы

Добавить в `Makefile` (или `scripts/`) команду:

```makefile
api-schema:
	python manage.py spectacular --validate --file api-schema.yaml
```

Прогон:
```bash
python manage.py spectacular --validate --file api-schema.yaml
# api-schema.yaml появляется в корне проекта
```

### Шаг 2. Frontend — script

`frontend/package.json` уже содержит:
```json
"generate:api-types": "openapi-typescript ../api-schema.yaml -o src/shared/api/schema.d.ts"
```

Проверить:
```bash
cd frontend
pnpm install
pnpm generate:api-types
# создаётся src/shared/api/schema.d.ts (~500-1500 строк)
```

### Шаг 3. Замена `types.ts`

Старый ручной `types.ts` оставляем как **алиасы** для удобства, но базовые типы — из `schema.d.ts`:

```ts
// frontend/src/shared/api/types.ts
import type { components } from './schema.d'

export type Schemas = components['schemas']

// Удобные алиасы — короче, чем Schemas['DisplayDetail']
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

// Не из схемы, а наш помощник
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

### Шаг 4. CI hook

`.github/workflows/ci.yml`:

```yaml
- name: Generate OpenAPI schema
  run: python manage.py spectacular --validate --file api-schema.yaml

- name: Check schema is up to date in repo
  run: |
    if ! git diff --exit-code api-schema.yaml; then
      echo "❌ api-schema.yaml не синхронизирован. Запустите python manage.py spectacular --file api-schema.yaml"
      exit 1
    fi

- name: Frontend typecheck
  working-directory: ./frontend
  run: |
    pnpm install --frozen-lockfile
    pnpm generate:api-types
    pnpm typecheck
```

### Шаг 5. Workflow

В `frontend/README.md` добавить раздел:

```markdown
## Когда меняется API

1. Backend кодер обновляет код
2. Прогоняет `python manage.py spectacular --file api-schema.yaml`
3. Коммит включает обновлённый `api-schema.yaml`
4. Frontend кодер делает `pnpm generate:api-types` локально
5. Видит новые / изменённые типы в `schema.d.ts`
6. Адаптирует код
```

### Шаг 6. Проверка

```bash
# 1. Бекенд: схема валидна
python manage.py spectacular --validate

# 2. Фронт: типы регенерятся без ошибок
cd frontend
pnpm generate:api-types

# 3. Тайпчек проходит
pnpm typecheck
```

---

## Критерии приёмки

- [ ] `api-schema.yaml` в корне репо
- [ ] `frontend/src/shared/api/schema.d.ts` генерируется по `pnpm generate:api-types`
- [ ] `frontend/src/shared/api/types.ts` — алиасы поверх `schema.d.ts`, не ручные определения
- [ ] CI шаг «schema in sync» работает
- [ ] `pnpm typecheck` зелёный после регенерации
- [ ] Все импорты в frontend используют типы из `types.ts` (не `schema.d.ts` напрямую)

---

## Что НЕ делать

- НЕ редактировать `schema.d.ts` руками — он генерится
- НЕ генерить типы при каждом dev-старте — только при изменении схемы
- НЕ хранить `api-schema.yaml` вне репо — он часть контракта
