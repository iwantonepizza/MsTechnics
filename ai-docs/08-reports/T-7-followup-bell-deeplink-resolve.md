# T-7-followup-bell-deeplink-resolve

> **PR:** не открыт
> **Автор:** GPT-5 Codex
> **Дата:** 2026-05-20
> **Статус задачи в 03-tasks/:** review

---

## Что сделано

- В `NotificationInboxItemSerializer` добавлено computed-поле `deep_link_path` для `application`, `departure` и `panel`.
- В inbox view добавлен batch-resolve target-объектов (`Application`, `Departure`, `Panel`) без N+1 на каждый notification.
- `NotificationBell` теперь использует `deep_link_path` с backend как приоритетный источник и оставляет старый fallback при `null`.
- Добавлен backend-тест на `/api/v1/notifications/inbox/` и обновлён frontend-тест колокольчика.

---

## Архитектурные решения

- Выбран вариант B из task-card: расширение `NotificationInboxItemSerializer`, без отдельного `resolve-link` endpoint.
- Department для `application` deeplink вычисляется по `notification.recipient.permission`; для `admin/all/technical/none_type` используется fallback `control`.
- Для `panel` deeplink уточнён маршрут до `/zip/{display.slug}?panel_id={id}`, если панель привязана к экрану.

---

## Тесты

- Backend:
  - `pytest apps/interface/tests/test_notifications_inbox.py`
- Frontend:
  - `npm test -- src/widgets/navigation/NotificationBell.test.tsx`
- Infra/schema:
  - `manage.py spectacular --skip-checks --validate --file api-schema.yaml`
  - `npm run generate:api-types`

---

## Ограничения и замечания

- `drf-spectacular` после регенерации всё ещё показывает pre-existing warnings/errors по `health`, `dashboard`, `activity`, path params и component-name collisions; новые warnings по `NotificationInboxItemSerializer` после добавления type hints сняты.
- `api-schema.yaml` и `frontend/src/shared/api/schema.d.ts` в этом репозитории уже имеют широкий unrelated diff; я не откатывал его вручную.

---

## Миграции

N/A
