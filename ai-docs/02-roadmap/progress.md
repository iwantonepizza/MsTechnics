# Прогресс проекта

**Текущая фаза:** Фаза 5 (Integrations) — функциональная часть и оба hotfix в review; единственный остаточный gate перед staging — `T-5-fix-003` (live-DB verification 19 alignment-миграций).
**Процент готовности:** ~92% (graph/state blocker снят кодером в T-5-fix-001/002, нужен один прогон migrate на копии прод-БД)
**Последнее обновление:** 2026-05-06 (Claude Opus, followup-review после hotfix-раунда)

---

## Статус по фазам

| Фаза | Готовность | Примечание |
|------|------------|------------|
| 0. Архитектура | ✅ 100% | |
| 0.5. Дизайн-эталон | ✅ 100% | Display View v2 + Main Menu v2 приняты, ждём ещё 5 экранов |
| 1. Фундамент | ✅ 95% | T-1-005 (CI) отложен до прод-репо |
| 2. Модели и миграции | ✅ 95% | 16/19 done; ждут пауз: T-2-021, T-2-023, T-2-024 |
| 3. REST API | ✅ 100% | 20 задач done + 2 hotfix done |
| 4. React SPA | ✅ 90% | основные экраны/модалки/SSE/OpenAPI types в review; остаются staging polish и дизайнерские follow-up |
| 5. Integrations | 🟡 85% | notifications, TG proxy, MAX, VNNOX, timers в review; T-5-050 blocked до SPA prod + 2 недели |

---

## Что сделано в этом раунде

### Hotfixes Фазы 3

- **T-3-fix-001:** ✅ done. Миграция `0004_strip_application_prefix.py`. Имена в БД синхронизированы с api-contract.md.
- **T-3-fix-002:** ✅ done. RefreshView блэклистит, destroy() whitelist подход.

### Фаза 4

- **T-4-001 (tokens):** ✅ done. tokens.css + Tailwind config с CSS-vars.
- **T-4-002 (OpenAPI types):** ✅ review. `api-schema.yaml` и `frontend/src/shared/api/schema.d.ts` сгенерированы, `types.ts` переведён на aliases.
- **T-4-003 (routing):** ✅ done. BrowserRouter + RequireAuth.
- **T-4-004 (Header):** ✅ done. SSE-индикатор + nav counts.
- **T-4-013 (DisplayViewPage):** ✅ done. 357 строк, role-based, новые статусы.
- **T-4-020 (TransitionModal):** ✅ done базово, transitionConfigs.ts на месте.
- **T-4-030 (SSE):** ✅ done. sse.ts с reconnect/backoff, useSSESubscription инициализирована в App.
- **T-4-032 (skeleton/states):** ✅ done. useDeferredLoading.ts.

### Фаза 5

- **T-5-001/T-5-002/T-5-006:** ✅ review. Notification models/channels/dispatcher/triggers.
- **T-5-010/T-5-011:** ✅ review. Telegram proxy healthcheck, legacy `sender_tg_message.py`/`tg_sender` удалены после снятия блока.
- **T-5-020:** ✅ review. MAX channel + webhook + `/start <username>` binding через `MsUser.max_id`.
- **T-5-030..033:** ✅ review. VNNOX Gmail parser, `AlarmEvent`, DisplayView VNNOX tab, unresolved alarm notifications.
- **T-5-040/041:** ✅ review. `daily_checker.py` и `ManageControl.py` удалены, systemd timers добавлены.
- **T-5-050:** blocked до SPA в prod/staging stability window.

### Новое / синхронизация

- `apps/interface/api/v1/dashboard/` — endpoint для KPI-strip MainMenu.
- `Makefile` с командами api-schema/fe-types/dev-setup.
- Добавлен `ai-docs/06-integrations/phase-5-rollout-runbook.md`.
- Добавлены отчёты по T-3 hotfix и ключевым T-4/T-5 задачам.
- **T-1-008:** ✅ review. Optional Sentry init, request_id/user_id context middleware, docker log rotation.
- `ai-docs/03-tasks` синхронизирован: `T-5-fix-001` и `T-5-fix-002` в `review`; свободных `ready` задач нет.
- `T-5-fix-002`: `.venv` теперь поднимает `pytest/ruff/black/mypy/factory-boy/freezegun`, `requirements.txt` в UTF-8, `pytest --collect-only` собирает 79 тестов.
- `T-5-fix-001`: legacy duplicate-model blocker снят, `python manage.py check` зелёный, `python manage.py makemigrations --check --dry-run` -> `No changes detected`.

---

## Что НЕ доделано

### Критично (блокеры staging)

- **T-5-fix-003** — live-DB verification: 19 state-only alignment-миграций ещё ни разу не прогонялись на живой БД (`migrate --plan/migrate` упал на `getaddrinfo failed`). Без сравнения схем `clean ↔ prod-after-migrate` нельзя гарантировать, что физическая прод-схема совпадает с тем, что Django state теперь утверждает. См. `08-reports/architect-review-2026-05-06-followup.md`.
- Прод-БД дамп от владельца — нужен для Шага 3 в T-5-fix-003.
- Перед prod/staging переключением заполнить реальные env: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_PROXY_URL`, `MAX_*`, Gmail OAuth token. См. `phase-5-rollout-runbook.md`.

### Серьёзно

- Backend coverage полностью не измерен: tooling поднят, точечный smoke 9/9 зелёных, но 79 collected pytest-ов на живой БД ещё не прогонялись. Закрывает T-5-fix-003.
- Frontend coverage `≥ 60%` (чек-лист Фазы 4) — заявлено зелёным, но конкретного числа в отчётах нет. Попросить кодера прогнать `npm run test -- --coverage` отдельным шагом.
- T-3-fix-001/T-3-fix-002, T-4-*, T-5-001..040 в `03-tasks/README.md` всё ещё `review` — архитектор переведёт их в `done` **одной волной** после T-5-fix-003 (раньше нет смысла, т.к. live-DB прогон может выявить регрессии в любой из этих задач).

### Backlog (P3, после prod stable)

- `T-5-fix-002-followup` — `ruff/black/mypy` baseline (291/96/16). Blocked корректно.
- `Executor → MsUser` явный FK (вместо текущего поиска по совпадению `telegram_id`). Не P0.
- Переезд `AUTH_USER_MODEL='user.MsUser'` → `apps.core.users.MsUser`. Отдельная итерация, требует пересоздания auth-таблиц.
- ADR «proxy-models pattern для legacy compat при переезде Django apps» — задокументировать решение из `zip/models.py`.

### В работе

- Staging smoke по `phase-5-rollout-runbook.md`.
- Дизайн/UX polish оставшихся SPA экранов после просмотра владельцем.

---

## Что заблокировано

| Что | Чем | Когда |
|-----|-----|-------|
| T-2-021 (drop 28 fields) | T-2-020 deploy + 2 нед | май-июнь 2026 |
| T-2-023 (backfill ActivityLog) | прод-данные | владелец даёт дамп |
| T-2-024 (drop legacy history) | T-2-023 + 2 нед | июнь 2026 |
| T-5-050 (legacy cleanup) | SPA в проде/staging + 2 недели без отката | июль-август 2026 |

---

## Что заблокировано владельцем

| Запрос | Куда |
|--------|------|
| Поля DisplaySpec (задача 16) | Фаза 2/4 — не блокер |
| Поля сортировки tabs (задача 6) | T-4-013 — UX можно без |
| Корп. номер для MAX-бота | T-5-020 |
| MAX bot token | T-5-020 smoke |
| Доступ на VPS вне РФ | T-5-010 smoke |
| Прод-БД дамп | T-2-001, T-3-fix-001 |

---

## Roadmap (примерные даты)

- **Май 2026:** staging smoke новых SPA + integrations, реальные env и Telegram/MAX/VNNOX проверки
- **Июнь:** фиксы после staging smoke, подготовка prod cutover
- **Июль:** деплой SPA/integrations на staging/prod по runbook
- **Август:** мониторинг staging, T-2-021/024, T-5-050 cleanup
- **Сентябрь 2026:** прод-релиз
