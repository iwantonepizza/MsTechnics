# Прогресс проекта

## Актуальный production-статус — 2026-06-05

Production cutover выполнен, секреты ротированы владельцем, активный `main` развёрнут через git.
Предыдущие упоминания ниже о pending cutover/owner rotation сохранены как исторический контекст и больше не являются текущими блокерами.

- `T-8-107` развёрнут на production, статус `review`: устранены activity request-loop и усиление `429`,
  исправлены retry списка городов/экранов и мобильное поведение камеры.
- `T-8-111` развёрнут на production, статус `done`: закрыты owner UX fixes, media reconciliation,
  history reset и production smoke.
- `T-8-108` закрыт через `T-8-111`: отсутствующие media references и подтверждённые заглушки очищены.
- `T-8-112` закрыт: public `/metrics` закрыт, fail2ban включён, health aliases проверены, VNNOX/backup blockers зафиксированы.
- Native Gunicorn переведён на gevent для SSE; отдельный nginx SSE location не пишет query-token в access log.
- PostgreSQL, Redis, Nginx, Gunicorn, daily tasks timer и VNNOX unresolved checker работают.
- Перед T-8-111 создан свежий scheduled DB dump и media tar backup; локальный backup timer работает.
- На VPS добавлен `/swapfile` 2 ГБ.
- Проверки T-8-111: backend `148 passed`, frontend `108 passed`, typecheck/build/check/migration drift — успешно.

### Оставшиеся задачи перед закрытием post-cutover окна

1. ✅ Поправить nginx routing для внешних `/health/live/` и `/health/ready/`: на 2026-06-05 public `/health/live` отдаёт JSON `200`.
2. VNNOX pull timer/Gmail OAuth: `mstechnics-vnnox-unresolved.timer` работает, `mstechnics-vnnox-pull.timer` не включён намеренно. Блокеры: нет `Config/token.pickle`, у `0/8` экранов заполнен `Display.vnnox_device_id`.
3. Подключить Prometheus/Grafana, внешний uptime и alerts. Public `/metrics` закрыт через Nginx (`403`), local `/metrics` доступен для scrape (`200`).
4. Настроить off-host encrypted backup и провести restore drill. Локальный `mstechnics-db-backup.timer` работает, off-host env не задан.
5. Усилить SSH: fail2ban установлен и active, jail `sshd` включён. Смену опубликованного пароля выполняет владелец; `PermitRootLogin`/`PasswordAuthentication` пока не менялись.
6. Провести ручную мобильную/визуальную приёмку камер, ролей и новых блоков после полного обновления SPA.

**Текущая фаза:** production развёрнут; идёт post-cutover стабилизация и ручная приёмка Phase 8.
**Процент готовности:** основной функционал развёрнут; `T-8-108`/`T-8-111` закрыты, остаются infra/observability задачи.
**Последнее обновление:** 2026-06-05 — production обновлён до infra/docs commit `47fef6e`, media/history cleanup выполнен; T-8-112 закрыл public `/metrics` и включил fail2ban. Проверки и логи зафиксированы в `08-reports/T-8-111.md` и `08-reports/T-8-112.md`.

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
| 6. Production cutover | ✅ развёрнут | Native production работает; секреты ротированы; backup/health/timers проверены. Остаются observability, off-host backup и SSH hardening. |
| 7. Product / redesign | 🟢 основной массив закрыт | ADR-002 rebranding; T-7-001/002/005/007/010/013/030/031/035/036/008/012/014 done; **T-7-100 Round 4 → review** (PR-1..13 закрыты, automated acceptance ✅); **T-7-003 Wave 1+2 → review**; полный трекер 36 задач в `phase-7-product/README.md` |
| 8. Owner Feedback Round 2 | 🟢 реализовано | Основной Round 2 и Round 2.1 развёрнуты. `T-8-107`, `T-8-108`, `T-8-111` закрывают prod request-loop/429, camera/VNNOX UX, media reconciliation и history reset. Остаётся ручная мобильная/визуальная приёмка и infra hardening. |

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
- **T-6-005 (P0 security, post-incident)** — coder-side готова: `scripts/check_gmail_oauth.py`, helper в `apps/integrations/gmail_alarms/services.py` (безопасный non-leaky output), обезличенный `.env.example`, `08-reports/security-incident-2026-05-13.md` (incident timeline + 8 секретов на ротацию). **Pending — owner-side ротация** (Google OAuth Client ID delete+recreate, `SECRET_KEY`, `DATABASE_PASSWORD`, BotFather `/revoke`, MAX reset token + `MAX_WEBHOOK_SECRET`, опционально Sentry DSN). **Перед prod cutover обязательно.** ✅ T-6-004 done.
- **T-6-006 (P1 hygiene)** — coder-side выполнена и стоит в `review`: добавлены `.editorconfig`, `.gitattributes`, `scripts/check_encoding.py`, pre-commit hook `check-encoding`, снят UTF-8 BOM с task cards, восстановлен битый `T-6-001`. Это preventive, чтобы повторение не убило центральный реестр снова.

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
| ~~T-2-021~~ | ~~prod-stable + 2 нед~~ — **разблокировано 2026-05-18** | ready |
| ~~T-2-023~~ | ~~ждали прод-данных~~ — дамп есть, **разблокировано** | ready |
| ~~T-2-024~~ | ~~T-2-023 + 2 нед~~ — **разблокировано** | ready |
| ~~T-5-050~~ | ~~prod + 2 нед~~ — **разблокировано 2026-05-18** | ready |
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

## Roadmap (свободный темп — владелец 2026-05-17 «не горит»)

Жёстких дат нет. Порядок шагов:

1. Кодер закрывает **T-6-001** (cutover runbook). После — `done`.
2. Владелец делает owner-side **T-6-005** (ротация секретов, ~30 минут).
3. Cutover на проде в **maintenance окно 22:00–08:00 МСК** (подтверждено: пользователи работают только днём).
4. **2 недели наблюдения** prod-stable.
5. Параллельно с (4) — T-6-002 (backup) + T-6-003 (observability).
6. После (4): T-5-050 (legacy cleanup), T-2-021/023/024 (Phase-2 паузы), T-5-fix-002-followup-ruff.
7. Phase 7 (продуктовая разработка): T-7-001/002/005/007/010/013 могут идти параллельно с (4)–(6), они frontend/UI не блокируют backend cutover.

Никакой спешки. Каждый шаг — только после зелёного `done` предыдущего.
