# Production hotfix. SSE, ZIP photo preview, activity backfill

> **PR:** pending
> **Автор:** GPT-5 Codex
> **Дата:** 2026-06-04
> **Статус задачи в 03-tasks/:** operational hotfix, без отдельной задачи

---

## Что сделано

- Исправлена SSE-подписка SPA: поток подключается внутри authenticated layout и переподключается при изменении access token.
- В ZIP добавлен крупный просмотр фото расходника из модалки редактирования.
- Расширены фильтры истории заявок/панелей/мест под смешанные event_type старого backfill и нового ActivityLog.
- Backfill legacy display history дополняет payload полями `cell_id` и `cell_position`.
- Добавлена и применена prod-миграция daily tasks `0004_convert_city_fk_to_id`.
- Daily task checker переведён на обновление статусов через `DailyTask.check_iteration`.

---

## Отклонения от плана

- Внесён operational hotfix без ожидания отдельной задачи архитектора, потому что проблемы проявились на проде после большого cutover.
- Архитектурные документы не менялись: изменения не вводят новую архитектуру, а восстанавливают контракт уже описанного ActivityLog/SSE.

---

## Тесты

- Добавлен backend-тест на фильтр истории места по legacy `legacy_slot_id`.
- Обновлён frontend-тест истории заявок под явный список event types.
- Локальный `py_compile` пройден.
- Локальные `pytest/manage.py check/vitest` не стартовали из-за отсутствующих зависимостей в локальном окружении (`structlog`, `node_modules`). Финальные проверки выполняются на production venv/node_modules перед выкладкой.

---

## Миграции

- Количество миграций: 1
- Тип: structure/data-safe conversion
- Протестировано на копии прод-БД: да, перед применением на проде
- Оценка времени на проде: секунды
- План отката: восстановление из frozen dump перед cutover

---

## Дальнейшие шаги

- Прогнать `backfill_activity_log` на проде и сверить `verify_activity_log`.
- Завершить owner-only ротацию секретов из `T-6-005`.
- Настроить Gmail OAuth token для VNNOX и заполнить `Display.vnnox_device_id`.
