# Phase 2 — Сводный отчёт блока

> **Автор:** Claude Sonnet (backend-кодер)
> **Дата:** 2026-04-24
> **Статус:** done (T-2-001..T-2-026, T-2-040, T-2-041)

---

## Выполненные задачи

| Задача | Статус | Примечание |
|--------|--------|------------|
| T-2-001 | ✅ done | scripts/dump_prod.sh, restore_to_dev.sh, scrub_pii.sql, bootstrap_dev.sh |
| T-2-002 | ✅ done | tests/factories.py — все основные модели |
| T-2-003 | ✅ done | tests/test_fsm.py — 12 тестов FSM + PanelMover + ActivityLog |
| T-2-010 | ✅ done | MsServiceControl/ → config/ |
| T-2-011 | ✅ done | apps/ skeleton + shared/exceptions.py + shared/time.py |
| T-2-012 | ✅ done | apps/core/references + apps/core/users + compat shims |
| T-2-013 | ✅ done | apps/directory/{displays,panels,storage} + zip/ shim |
| T-2-014 | ✅ done | apps/workflow/{applications,departures} + shims |
| T-2-020 | ✅ done | ApplicationEvent модель + миграция |
| T-2-022 | ✅ done | ActivityLog + ActivityLogger сервис |
| T-2-026 | ✅ done | ConcreteMsUser удалён |
| T-2-040 | ✅ done | ApplicationStateMachine (7 переходов декларативно) |
| T-2-041 | ✅ done | PanelMover (блокировка при активной заявке — задача #8) |

## Отложены (требуют прод-данных или ждут паузы)

| Задача | Причина |
|--------|---------|
| T-2-021 | Ждёт 2 недели после T-2-020 (удаление 28 полей) |
| T-2-023 | Backfill ActivityLog — требует прод-данных |
| T-2-024 | Удаление legacy history таблиц — после T-2-023 + паузы |
| T-2-025 | FK name→id — Фаза 3, после полного переноса моделей |
| T-2-027 | Display.save() side effects → DisplayFactory |
| T-2-028..030 | Независимые небольшие задачи |

---

## Архитектурные решения

**MDL-010 исправлен:** `if Panels:` (класс, всегда truthy) → `if panel is not None:` в `main/Db/orm_query.py`.

**ApplicationStateMachine:** 7 переходов декларативны. Каждый переход:
- Проверяет права (allowed_roles)
- Создаёт ApplicationEvent
- Запускает хуки (condition change, panel status sync)
- Пишет в ActivityLog

**PanelMover:** запрещает перемещение при `application.status.name in ACTIVE_APPLICATION_STATUSES`.

**Compat shims:** все старые import-пути работают через shim-файлы. Views не трогаем до Фазы 3.

---

## ⚠️ Требует действий перед деплоем

1. На реальной машине: `python manage.py migrate` создаст таблицы `activity_log` и `application_event`
2. `SeparateDatabaseAndState` миграции — проверить на копии прода через `scripts/bootstrap_dev.sh`
3. `pre-commit install` после `pip install pre-commit`

---

## Вопросы архитектору

1. `pandas/numpy` в prod-зависимостях — оставить или вынести в `[scripts]` extra?
2. `DailyTask` модель сейчас в `zip/models.py` (legacy). Куда переносить — `apps/workflow/daily_tasks/`?
3. `Contact` модель в `departure/models.py` — она используется? Не нашёл views для неё.
