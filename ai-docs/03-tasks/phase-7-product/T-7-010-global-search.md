# T-7-010. Глобальный поиск через `/`

> **Тип задачи:** backend + frontend
> **Приоритет:** P2 (после T-7-002 design tokens)
> **Оценка:** 4-6 часов (2-3 backend search endpoint + 2-3 frontend palette UI)
> **Фаза:** 7
> **Статус:** review
> **Исполнитель:** GPT-5 Codex

---

## Цель

Закрыть X1: глобальный поиск через клавишу `/` (или `Cmd+K`) с возможностью искать **по всем 6 категориям** одновременно: экраны, панели, заявки, выезды, юзеры, ЗИП-расходники. Минимальное Cmd+K поведение: ввёл фрагмент → видишь сгруппированный список результатов → Enter переходит на сущность.

---

## Контекст

Ответ владельца 2026-05-16:

> **X1.** Поиск глобальный (на всех страницах через шорткат /): **да, все возможности из списка**

Список (6 категорий):
- Экраны (`Display`)
- Панели (`Panel`)
- Заявки (`Application`)
- Выезды (`Departure`)
- Юзеры (`MsUser`)
- ЗИП-расходники (`Wires`, `Hubs`, `Lamels` + после T-7-005 `PowerBlocks`, `Connectors`)

---

## Зависимости

- **Блокируется:** ничем для бэкенда. Для frontend — T-7-002 (tokens v2) желательно, чтобы palette UI был в актуальном стиле.
- **Блокирует:** ничего.

---

## Архитектурное решение

**Один endpoint `GET /api/v1/search/?q=<term>&limit=20`** с группировкой результатов по типам:

```json
{
  "displays": [
    {"id": 12, "slug": "rk-1", "name": "РК-1", "city": "Ижевск", "score": 0.9}
  ],
  "panels": [
    {"id": 234, "name": "P-007", "display": "РК-1", "condition": "work", "score": 0.8}
  ],
  "applications": [
    {"id": 5, "panel": "P-007", "status": "sent_to_service", "created_at": "...", "score": 0.7}
  ],
  "departures": [...],
  "users": [...],
  "storage": [...]
}
```

Поиск — **PostgreSQL trigram similarity** (`pg_trgm` extension) или простой `icontains` для старта. Trigram даст fuzzy match («рк1» найдёт «РК-1», «иван» найдёт «Иванов»).

`limit` применяется **к каждой категории отдельно** (20 экранов + 20 панелей + …), не к общей выдаче.

**Permission scoping:** результаты фильтруются по `request.user.allowed_city` (для экранов / панелей / заявок) и текущим ролям. Юзер видит только то, к чему имеет доступ. Без этого поиск утечёт inventory чужих городов.

---

## Что нужно сделать

### Backend

1. **Миграция:** `CREATE EXTENSION IF NOT EXISTS pg_trgm` (Postgres extension). Отдельная миграция в `apps/interface/api/v1/search/migrations/0001_pg_trgm.py`.

2. **Endpoint:** `apps/interface/api/v1/search/views.py`:

   ```python
   class GlobalSearchView(APIView):
       permission_classes = [IsAuthenticated, IsAnyRole]

       def get(self, request):
           q = request.query_params.get("q", "").strip()
           if len(q) < 2:
               return Response({"error": "min 2 chars"}, status=400)
           limit = min(int(request.query_params.get("limit", 10)), 20)

           data = {
               "displays": self._search_displays(q, limit, request.user),
               "panels": self._search_panels(q, limit, request.user),
               "applications": self._search_applications(q, limit, request.user),
               "departures": self._search_departures(q, limit, request.user),
               "users": self._search_users(q, limit, request.user),
               "storage": self._search_storage(q, limit, request.user),
           }
           return Response(data)
   ```

   Каждый `_search_X` — отдельный helper, использует `TrigramSimilarity` из `django.contrib.postgres.search` или, как минимум, `icontains` по name/description/comment.

3. **Permission scoping** в каждом `_search_X` — фильтр по `request.user.allowed_city.all()` для модели, имеющей `city` FK; для `MsUser` — только админу.

4. **Тесты:**
   - 2 char minimum — 400.
   - Найти display по slug, panel по name, application по comment.
   - Юзер с одним allowed_city не видит displays других городов.
   - 6/6 категорий возвращают пустые массивы при отсутствии совпадений.

5. **OpenAPI schema** обновить (`make api-schema` + commit).

### Frontend

1. **Shortcut handler** в `frontend/src/app/App.tsx` или `Header`:

   ```ts
   useEffect(() => {
     const onKey = (e: KeyboardEvent) => {
       if ((e.key === "/" || (e.key === "k" && (e.metaKey || e.ctrlKey)))
           && !["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName ?? "")) {
         e.preventDefault()
         setOpen(true)
       }
     }
     window.addEventListener("keydown", onKey)
     return () => window.removeEventListener("keydown", onKey)
   }, [])
   ```

2. **`<CommandPalette>` компонент** в `shared/ui/`:
   - Modal overlay поверх любой страницы.
   - Input с focus on mount.
   - React Query: `useQuery(['search', q], () => api.get('/search/', { params: { q, limit: 8 }}))` с debounce 200ms.
   - 6 секций (Экраны / Панели / Заявки / Выезды / Юзеры / ЗИП), каждая с заголовком и до 8 результатов.
   - Стрелки ↑↓ для навигации, Enter — переход на сущность.
   - Esc — закрыть.
   - Подсветка matched-фрагмента через `<mark>` (это «маркерное выделение» из брендбука — здесь уместно).

3. **Routing**: каждый результат имеет `to`:
   - Display → `/displays/{slug}`
   - Panel → `/displays/{display_slug}#panel-{name}`
   - Application → `/applications/{id}`
   - Departure → `/departures/{id}`
   - User → `/admin/users/{username}` (только админу)
   - Storage item → `/zip#{type}-{name}`

4. **Empty state**: «Введите запрос (минимум 2 символа)».

5. **Tests** (vitest + RTL):
   - `/` открывает modal.
   - Esc закрывает.
   - Mock-ответ из 6 категорий рендерится корректно.

---

## Критерии приёмки

- [ ] `pg_trgm` extension в миграции.
- [ ] `GET /api/v1/search/?q=...` — 200, валидная схема ответа.
- [ ] Permission scoping: юзер видит только разрешённые города.
- [ ] OpenAPI schema обновлена.
- [ ] Backend pytest для search — зелёный.
- [ ] Frontend `/` и `Cmd+K` открывают palette везде, кроме input/textarea.
- [ ] Navigation Enter работает для всех 6 типов.
- [ ] Debounce 200 ms — нет лишних запросов.
- [ ] Vitest зелёный.
- [ ] Smoke в обеих темах (light/dark).
- [ ] Отчёт `08-reports/T-7-010.md`.

---

## Что НЕ делать

- Не индексировать через Elasticsearch / Meilisearch. PostgreSQL `pg_trgm` достаточно для нашего масштаба (8 displays, 2333 panels, 10 applications).
- Не возвращать всё содержимое объектов — только короткое preview (id, name, slug, contextual hint).
- Не фильтровать на frontend — фильтрация прав строго на backend.
- Не делать highlights через innerHTML — XSS. Только через React `<mark>` или structured chunks.

---

## Вопросы для архитектора

- [ ] Нужны ли metrics (top searches, no-result queries) для последующей оптимизации? — **Ответ:** не в этой задаче, follow-up если потребуется.
- [ ] Сохранять recent searches в localStorage? — **Ответ:** да, до 5 последних. Это UX-улучшение, делается в этой же задаче.

---

## Отчёт по выполнению

(Заполняет кодер.)
