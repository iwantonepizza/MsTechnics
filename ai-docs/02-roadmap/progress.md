# Прогресс проекта

**Текущая фаза:** Фаза 6 (Production cutover). Все Фазы 1-5 закрыты (review→done после T-5-fix-003). На сервере у владельца — ошибка миграций из-за конфликта `prod_dump_compat.sql` ↔ forward-only migrations. Разруливает `T-6-001`.
**Процент готовности:** ~96% (Phase 5 закрыт, остаются runbook + post-cutover задачи)
**Последнее обновление:** 2026-05-07 (Claude Opus, апрув T-5-fix-003 + постановка T-6-001..004)

---

## Статус по фазам

| Фаза | Готовность | Примечание |
|------|------------|------------|
| 0. Архитектура | ✅ 100% | |
| 0.5. Дизайн-эталон | ✅ 100% | Display View v2 + Main Menu v2 приняты, остаются 5 экранов на polish |
| 1. Фундамент | ✅ 100% | T-1-005 (CI) blocked до prod-репо — не блокер кода |
| 2. Модели и миграции | ✅ 95% | done; ждут пауз: T-2-021, T-2-023, T-2-024 |
| 3. REST API | ✅ 100% | 20 задач done + 2 hotfix done |
| 4. React SPA | ✅ 100% | все экраны/модалки/SSE/OpenAPI типы done; staging polish/coverage — на post-cutover |
| 5. Integrations | ✅ 100% | notifications/TG/MAX/VNNOX/timers done; 3 hotfix done; T-5-050 blocked до prod+2нед |
| 6. Production cutover | 🟡 0% → starts now | T-6-001..004 ready |

---

## Что закрыто после T-5-fix-003

### Hotfix Фазы 5 (T-5-fix-001/002/003)

- **T-5-fix-001 done.** Legacy models → shim/proxy, state-only DeleteModel, 19 alignment миграций.
- **T-5-fix-002 done.** dev/test extras в `.venv`, UTF-8 `requirements.txt`, bootstrap-скрипты обновлены.
- **T-5-fix-003 done.** На копии прод-БД (`db_dumps/mstechnics.dump`) полный цикл `restore → migrate → smoke` отработал. **Реальные данные:** 7 users, 8 displays, 2333 panels, 10 applications. HTTP smoke зелёный. pytest 79/79, coverage 57%.

### Forward-only data migrations добавлены

- `apps/core/users/migrations/0003_align_user_physical_schema.py` — `max_id` + `telegram_id` varchar(20).
- `apps/directory/displays/migrations/0005_convert_display_city_fk_to_id.py` — конверсия `display.city_id`.
- `apps/directory/displays/migrations/0006_convert_cell_fk_storage_to_id.py` — конверсия `cell.display_id/panel_id`.
- `apps/directory/panels/migrations/0004_convert_panel_fk_storage_to_id.py` — конверсия `panel.{display,condition,department}_id`.

Все с `atomic=False`, RunSQL backfill + RunPython validation + RENAME COLUMN. Это идиоматичный Django путь для крупной prod-data migration.

### review → done одной волной

- T-1-008 (prod logging) → done
- T-3-fix-001, T-3-fix-002 → done
- T-4-001..T-4-032 (13 задач Phase 4) → done
- T-5-001..T-5-040 (7 задач Phase 5) → done
- T-5-fix-001, T-5-fix-002, T-5-fix-003 → done

---

## Что НЕ доделано

### Критично (блокеры prod cutover)

- **T-6-001 (P0)** — production cutover runbook. На сервере владельца сейчас ошибка миграций из-за конфликта `scripts/prod_dump_compat.sql` ↔ forward-only migrations из T-5-fix-003. Карточка прописывает: удалить compat-патч, переписать `restore_to_dev.sh`, прогнать на staging-копии, написать step-by-step runbook для владельца. См. `08-reports/architect-review-2026-05-07-prod-cutover.md`.
- **T-6-004 (P0 security)** — прод-дамп `db_dumps/mstechnics.dump` (и `mstechnics.dump` в корне) могут быть в git. Это PII утечка. Закрыть `.gitignore`, при необходимости — `git filter-repo`.

### Серьёзно (нужно до закрытия post-cutover окна)

- **T-6-002 (P1)** — backup strategy. Без операционного backup'а первый сбой = потеря данных.
- **T-6-003 (P1)** — observability (django-prometheus + Grafana + uptime + 4 alerts). Без этого падение прода обнаруживается по жалобе пользователя.

### В наблюдении (post-cutover, 2 недели stable)

- T-2-021 (drop 28 fields), T-2-023 (backfill ActivityLog), T-2-024 (drop 5 history) — Phase-2 паузы.
- T-5-050 (templates/views/shims cleanup) — blocked до 2 недель prod-stable.
- T-5-fix-002-followup-ruff — lint baseline (291/96/16) — blocked до cutover.

### Backlog (P3, после prod-stable)

- ADR-002 «proxy-models pattern для legacy compat при переезде Django apps» (то, как сделан `zip/models.py`).
- `Executor → MsUser` явный FK (вместо matching по `telegram_id`).
- Переезд `AUTH_USER_MODEL='user.MsUser'` → `apps.core.users.MsUser`. Большая отдельная итерация.
- Frontend coverage measurement (`npm run test -- --coverage`).

---

## Что заблокировано

| Что | Чем | Когда |
|-----|-----|-------|
| T-2-021 (drop 28 fields) | T-2-020 deploy + 2 нед prod-stable | июнь 2026 |
| T-2-023 (backfill ActivityLog) | прод-данные (есть в `db_dumps/`, но backfill требует анализа форматов) | май-июнь 2026 |
| T-2-024 (drop legacy history) | T-2-023 + 2 нед | июнь-июль 2026 |
| T-5-050 (legacy cleanup) | prod + 2 нед без отката | июль-август 2026 |
| T-5-fix-002-followup-ruff | вне staging churn | после cutover |
| T-1-005 (CI) | прод-репо | когда переедем в нормальный git-репо |

---

## Что заблокировано владельцем

| Запрос | Куда |
|--------|------|
| Поля DisplaySpec (задача 16) | долгосрочно, не блокер |
| Поля сортировки tabs (задача 6) | UX-улучшение, не блокер |
| Корп. номер для MAX-бота | T-5-020 smoke |
| MAX bot token | T-5-020 smoke |
| Доступ на VPS вне РФ | T-5-010 smoke |
| Старая прод-БД дамп | ✅ получен (`db_dumps/mstechnics.dump`) |

---

## Roadmap (новые даты)

- **Май 2026 — текущая неделя:** T-6-001 (production cutover runbook) + T-6-004 (gitignore/leak check). Реальный cutover на сервере владельца.
- **Май-июнь:** T-6-002 (backup) + T-6-003 (observability). Наблюдение прода 2 недели.
- **Июнь-июль:** T-5-050 (legacy cleanup) + T-2-021/023/024 (Phase-2 паузы).
- **Июль-август:** T-5-fix-002-followup-ruff (lint baseline) + backlog задачи.
- **Сентябрь 2026:** проект закрыт, переход в обычную продуктовую разработку (15 задач владельца + long-tail).
