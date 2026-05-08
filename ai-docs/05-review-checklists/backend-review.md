# Backend Review Checklist

Чеклист для ревью backend PR. Архитектор проходит по нему. Если хотя бы один пункт красный — PR идёт на правки.

---

## Архитектура

- [ ] Бизнес-логика — в `services/`, **не** в views и **не** в models
- [ ] ORM-запросы — в `repositories/` (или `managers/`), не разбросаны по views
- [ ] Models — только данные + валидация (clean) + простые computed properties
- [ ] Нет импортов между приложениями, кроме как через `public.py` или `interfaces.py`
- [ ] Нет циклических импортов (проверить `python -c "import config.settings.dev"`)
- [ ] Нет нарушений слоистости из `ai-docs/00-architecture/layering.md`

## Код

- [ ] Все публичные функции/методы имеют типы
- [ ] `mypy` проходит, без `type: ignore` без комментария
- [ ] `ruff check` проходит
- [ ] `black` применён
- [ ] Нет `print(...)`
- [ ] Нет `except Exception:` без конкретики
- [ ] Нет `# type: ignore` без tracker-link
- [ ] Нет `# TODO` без tracker-link
- [ ] Нет debug-кода (`import pdb`, закомментированные строки, dev-endpoints)
- [ ] Импорты отсортированы (ruff I)
- [ ] Функции не длиннее 50 строк

## Django / ORM

- [ ] Мутации нескольких записей — в `transaction.atomic`
- [ ] Есть `select_related` / `prefetch_related` где ходим в FK в цикле
- [ ] Нет N+1 (проверить Debug Toolbar или запустить конкретный endpoint со счётчиком queries)
- [ ] FK имеет явный `on_delete`
- [ ] В ModelAdmin есть `list_display`, `search_fields`, `list_filter`
- [ ] Миграции:
  - [ ] Имя миграции осмысленное (не `auto_20240422_1234.py`)
  - [ ] Data-миграция — обратима (reverse_code задан) или явно помечена как non-reversible
  - [ ] Протестирована на копии прод-БД (отметить в PR-описании)
  - [ ] Миграция атомарна (либо `atomic = True`, либо явно `atomic = False` с обоснованием)

## DRF

- [ ] Serializer валидирует input, а не только сериализует output
- [ ] В view нет ручного парсинга JSON — через serializer
- [ ] В view нет бизнес-логики — вызов сервиса
- [ ] Permission_classes заданы явно, не `IsAuthenticated` везде без разбора
- [ ] Pagination задан, если возвращается список
- [ ] Поля serializer совпадают с `api-contract.md`

## Тесты

- [ ] Новые функции / методы покрыты тестами
- [ ] Новый view — минимум 3 теста (happy, 403, 422)
- [ ] Используются фабрики (factory_boy), не прямой `Model.objects.create`
- [ ] Coverage нового кода ≥ 80%
- [ ] Тесты не зависят от порядка выполнения
- [ ] Тесты не ходят по сети (mock'и)

## Безопасность

- [ ] Нет секретов в коде
- [ ] Все мутации идут через authenticated user
- [ ] SQL только через ORM (no raw SQL без параметров)
- [ ] File upload — валидация MIME, размер, magic bytes
- [ ] Ничего, что требует админ-прав, не открыто для обычного юзера
- [ ] Нет `redirect(request.META['HTTP_REFERER'])`

## Производительность

- [ ] Нет запросов в цикле (N+1)
- [ ] Queryset имеет `[:limit]` если результат рендерится в template/JSON без пагинации
- [ ] Нет синхронных HTTP-вызовов в обработчике request (Telegram, Gmail, etc) — через очередь

## Документация

- [ ] Если изменилась архитектура — обновлён `ai-docs/00-architecture/*.md`
- [ ] Если изменился API — обновлён `ai-docs/07-frontend/api-contract.md`
- [ ] Если появился новый паттерн — добавлен в `ai-docs/04-conventions/code-style.md`
- [ ] В коде: docstrings для публичного API

## Review-gotchas

На что я обращаю внимание особенно:

- Сервис, который зовут два разных контекста (view + signal + management command) — точно должен быть в service layer, не в модели
- «Быстро починил, рефакторнём потом» — **отклоняю**, заводим задачу и возвращаем в рефактор
- Magic numbers и magic strings — в constants
- Копипаста — в утилиты
- Бизнес-правило, не покрытое тестом, — не бизнес-правило, а случайность

## Отдельное: миграции с данными

Если в PR есть data-migration — дополнительно:

- [ ] Миграция идемпотентна (повторный запуск не ломает)
- [ ] Миграция обрабатывает edge-кейсы (пустые таблицы, NULL-ы)
- [ ] Миграция **не** удаляет данные без архивирования
- [ ] Миграция не использует models напрямую, только `apps.get_model(...)` (иначе break при future-changes)
- [ ] При большом объёме — batch-processing (через `.iterator(chunk_size=1000)`)
