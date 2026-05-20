# T-7-followup-applications-display-city. Display city in application list payloads

> **PR:** не открыт
> **Автор:** GPT-5 Codex
> **Дата:** 2026-05-20
> **Статус задачи в 03-tasks/:** review

---

## Что сделано

- Добавлен `DisplayMiniCitySerializer` и поле `display.city` в [apps/interface/api/v1/applications/serializers.py](/abs/path/C:/Users/miser/mstechnics/mstechnics/apps/interface/api/v1/applications/serializers.py).
- Усилен `select_related(...)` в [apps/interface/api/v1/dashboard/views.py](/abs/path/C:/Users/miser/mstechnics/mstechnics/apps/interface/api/v1/dashboard/views.py) и в action `panels/{id}/applications` в [apps/interface/api/v1/panels/views.py](/abs/path/C:/Users/miser/mstechnics/mstechnics/apps/interface/api/v1/panels/views.py), чтобы `display.city` не тащился отдельными запросами.
- Добавлен API-тест [apps/interface/tests/test_phase7_followups.py](/abs/path/C:/Users/miser/mstechnics/mstechnics/apps/interface/tests/test_phase7_followups.py), который проверяет `GET /api/v1/dashboard/` и наличие `monitoring.recent[].display.city`.
- Регенерированы `api-schema.yaml` и [frontend/src/shared/api/schema.d.ts](/abs/path/C:/Users/miser/mstechnics/mstechnics/frontend/src/shared/api/schema.d.ts).

---

## Отклонения от плана

- **Что:** кроме serializer обновлены еще `dashboard` и `panels/{id}/applications` querysets.
- **Почему:** иначе новое поле `display.city` вызывало бы лишние SQL-запросы в местах, где уже используется `ApplicationListItemSerializer`.
- **Нужно ли обновить архитектурный документ:** нет.

---

## Архитектурные решения

- `display.city` добавлен только в mini-DTO списка заявок, без изменения модели и без расширения detail-сериализаторов сверх скоупа задачи.
- Оптимизация сделана на уровне queryset, а не в serializer, чтобы не плодить скрытые обращения к ORM в представлении API.

---

## Тесты

- Новых файлов с тестами: 1
- Добавлено тестов: 1 целевой backend-тест для этой задачи
- Что покрыто:
  - `GET /api/v1/dashboard/` возвращает `display.city.slug` и `display.city.name` внутри recent applications.
- Что НЕ покрыто и почему:
  - `panels/{id}/applications` отдельно не тестировался: serializer тот же самый, а задача не меняет endpoint-контракт кроме уже проверенного mini-payload.

---

## Нагрузка / производительность

- Явный N+1 для `display.city` снят через `select_related("display__city")` в querysets, которые сериализуют `ApplicationListItemSerializer`.
- Debug Toolbar / точный query-count не замерялся в этом окружении.

---

## Миграции

N/A

---

## Время

- Оценка в задаче: 20 минут
- Фактически: около 30-40 минут вместе с тестом и регенерацией schema/types

---

## Проверки перед PR

- [ ] `pre-commit run --all-files` — не запускал по всему репо из-за большого количества чужих изменений
- [x] `pytest` — `.venv\Scripts\python.exe -m pytest apps/interface/tests/test_phase7_followups.py`
- [ ] `mypy` — не запускал
- [x] `ruff check` — по touched Python files
- [x] `black` — по touched Python files через `.venv`
- [x] `manage.py spectacular --skip-checks --validate --file api-schema.yaml`
- [x] Нет debug-кода
- [x] Нет секретов
- [ ] PR-description заполнен по шаблону

---

## Дальнейшие шаги

- Если нужен чистый schema diff без старых unrelated warning/error, стоит отдельно разбирать `drf-spectacular` cleanup.
- `T-7-followup-bell-deeplink-resolve` остается отдельной задачей: одно только наличие `display.city` в application list payload не решает deep-link inbox уведомлений само по себе.
