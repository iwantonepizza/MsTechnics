# Roadmap — план работ

Проект переписывается в 5 фаз. Фазы идут **последовательно**, пересечения между кодерами — только в рамках одной фазы и только на разных приложениях.

---

## Принципы планирования

1. **Работаем на прод-данных.** Миграции только forward, обязательно с data-migration. Любая миграция тестируется на копии прод-БД прежде, чем попасть в main.
2. **Тесты до рефакторинга.** Перед тем как трогать модель — покрыть её текущее поведение regression-тестами. Иначе не узнаем, что сломали.
3. **Фаза = 1-2 недели** при 2-3 часах/день. Каждая задача = до 3 часов.
4. **Фронт и бэк параллельно, начиная с фазы 3.** До этого — только backend: без нормализации моделей API разрабатывать бессмысленно.
5. **Каждая фаза завершается релизом в прод.** Не «все 5 фаз = один релиз». После фазы 1 прод должен быть в рабочем состоянии, даже если фронт старый.

---

## Фаза 1. Фундамент (безопасность, конфиг, типы)

**Цель:** убрать риски эксплуатации. Подготовить инфраструктуру для остального. **Код не меняет поведение.**

**Продолжительность:** ~15 часов (≈ 1 неделя)

| ID | Задача | Время | Зависимости |
|----|--------|-------|-------------|
| T-1-001 | Перевод зависимостей в `pyproject.toml` + `requirements.lock` | 1.5ч | — |
| T-1-002 | Правка `docker-compose`: postgres, env_files, сети | 2ч | T-1-001 |
| T-1-003 | Pre-commit hooks: ruff + black + mypy + djlint | 1.5ч | T-1-001 |
| T-1-004 | Заменить все `print(...)` на `structlog` | 2ч | T-1-001 |
| T-1-005 | CI: GitHub Actions — lint + test | 2ч | T-1-003 |
| T-1-006 | Фиксы критических багов: SEC-007 (registration), MDL-009 (signal), MDL-010 (if Panels) | 2ч | — |
| T-1-007 | Вынести секреты: `django-environ`, `.env.example`, отзыв Google secret (SEC-001..004) | 2ч | — |
| T-1-008 | `logging` в prod: structured JSON в stdout + sentry-sdk (опционально) | 1.5ч | T-1-004 |
| T-1-009 | Убрать `redirect(HTTP_REFERER)` — все случаи, на `safe_redirect` | 1ч | — |
| T-1-010 | Ограничить `applications_report` и `panel_reports` в views до 50 записей | 0.5ч | — |
| T-1-011 | Аудит `applications.all_new`, заменить на `applications.all` где не нужны архивные (задача владельца №7) | 1ч | — |

**Выход фазы 1:**
- Нет секретов в git
- `DEBUG` не протекает в прод
- `pytest && ruff && mypy` проходит
- CI зелёный на PR
- Прод работает как раньше, но стабильнее

---

## Фаза 2. Модели и миграции (денормализация)

**Цель:** нормализовать доменную модель под целевую архитектуру. Код старых views продолжает работать через compat-слой.

**Продолжительность:** ~25 часов (≈ 2 недели)

Все задачи фазы 2 имеют общее требование: **сначала regression-тесты на старое поведение, потом рефакторинг**.

### 2.1. Подготовка

| ID | Задача | Время |
|----|--------|-------|
| T-2-001 | Дамп прод-БД, импорт в dev, baseline тесты на миграцию | 2ч |
| T-2-002 | factory_boy фабрики для всех моделей | 3ч |
| T-2-003 | Regression-тесты на: `create_application`, `apply_application`, `delete_application`, `replace_panel_in_cell`, `change_panel_condition` | 4ч |

### 2.2. Реорганизация пакетной структуры

| ID | Задача | Время |
|----|--------|-------|
| T-2-010 | Переименовать `MsServiceControl/` → `config/`, обновить `manage.py`, `wsgi.py` | 1ч |
| T-2-011 | Создать структуру `backend/apps/{core,directory,workflow,activity,notifications,integrations,interface}/` (пока пусто) | 1.5ч |
| T-2-012 | Переместить `main` → `apps/core`, `user` → `apps/core/users` (миграция через Django migrations `RunPython` + `db_table`) | 3ч |
| T-2-013 | Переместить `zip` → `apps/directory`, переименовать `Panels` → `Panel` | 3ч |
| T-2-014 | Переместить `application` → `apps/workflow/applications`, `departure` → `apps/workflow/departures` | 2.5ч |

> На этом этапе код продолжает работать (compat imports через `__init__.py`), но физически файлы уже в новых местах.

### 2.3. Денормализация

| ID | Задача | Время |
|----|--------|-------|
| T-2-020 | Создать `ApplicationEvent` модель + миграция данных из `comment_*`/`time_*`/... | 3ч |
| T-2-021 | Удалить старые поля из `Application` (отдельная миграция после 2-недельной паузы) | 1ч |
| T-2-022 | Создать `ActivityLog` + ContentType | 2ч |
| T-2-023 | Миграция данных: 5 HistoryReport → ActivityLog | 3ч |
| T-2-024 | Удалить старые HistoryReport модели (после паузы) | 1ч |
| T-2-025 | FK `to_field='name'` → `to_field='id'` (основные модели, по одной миграции на модель) | 4ч |
| T-2-026 | Удалить `ConcreteMsUser` | 0.5ч |
| T-2-027 | Переписать `Display.save()` → `DisplayFactory.create()` | 2ч |
| T-2-028 | `Panel.application_status` — удалить поле, вычислять | 2ч |
| T-2-029 | `DailyTask.*_notification_sent` → `notified_stages: JSONField` | 1.5ч |
| T-2-030 | `Departure.status: CharField` → FK(DepartureStatus) + справочник | 1.5ч |

### 2.4. FSM

| ID | Задача | Время |
|----|--------|-------|
| T-2-040 | `ApplicationStateMachine` + `Transition` декларативно, unit-тесты | 3ч |
| T-2-041 | `PanelMover` (move между отделами) с валидацией активных заявок (задача владельца №8) | 2ч |

**Выход фазы 2:**
- Все HistoryReport в одной таблице `ActivityLog`
- Заявка нормализована, события в отдельной таблице
- Вся бизнес-логика в сервисах
- Test coverage ≥ 70%
- Прод работает. Старый фронт по-прежнему рендерит через compat-слой.

---

## Фаза 3. REST API + сервисы

**Цель:** бэкенд становится API-first. Фронт всё ещё старый, но через API-обёртку.

**Продолжительность:** ~20 часов (≈ 1.5 недели)

| ID | Задача | Время |
|----|--------|-------|
| T-3-001 | Установка DRF, SimpleJWT, drf-spectacular (Swagger) | 1ч |
| T-3-002 | Auth endpoints: login, refresh, logout, current user | 2ч |
| T-3-003 | Permissions classes (IsMonitoring, IsControl, IsService, HasCity) | 1.5ч |
| T-3-010 | API: Cities, Colors, Icons, Departments, Conditions (read-only) | 2ч |
| T-3-011 | API: Displays (list, detail), DisplaySpec | 1.5ч |
| T-3-012 | API: Panels (list, detail, move, change_condition) | 2.5ч |
| T-3-013 | API: Cells (read-only, вложенные в Display) | 1ч |
| T-3-014 | API: Applications (list, detail, transitions, transition) | 2.5ч |
| T-3-015 | API: Departures (CRUD + actions) | 2ч |
| T-3-016 | API: ActivityLog (list с фильтрами по target_type/target_id/event_type/actor) | 2ч |
| T-3-017 | API: Storage (Wires/Hubs/Lamels) | 1.5ч |
| T-3-018 | API: Users (читать, менять `allowed_cities` — только admin) | 1ч |
| T-3-019 | OpenAPI spec → `ai-docs/07-frontend/api-contract.md` автогенерация | 1ч |

**Выход фазы 3:**
- `/api/v1/...` покрывает 100% функционала UI
- Swagger `/api/v1/docs/`
- JWT работает
- Старый UI продолжает работать

---

## Фаза 4. React SPA

**Цель:** полностью заменить Django templates на React.

**Продолжительность:** ~30 часов (≈ 2-3 недели), параллельно с фазой 5

### Frontend (Claude Design ведёт)

| ID | Задача | Время |
|----|--------|-------|
| T-4-001 | Vite + React + TS + Tailwind + shadcn/ui init | 2ч |
| T-4-002 | Axios client + interceptor JWT refresh | 1.5ч |
| T-4-003 | Auth flow + protected routes | 1.5ч |
| T-4-004 | Layout: Header, Sidebar, NotificationToasts | 2ч |
| T-4-005 | Страница логина | 1ч |
| T-4-006 | Главное меню (`/menu`) | 2ч |
| T-4-007 | Страница «Мониторинг» — список городов → экранов → экран | 3ч |
| T-4-008 | Страница «Контроль» — список городов → экран + заявки | 2.5ч |
| T-4-009 | Страница «Сервис» — экран + FSM-кнопки заявок | 3ч |
| T-4-010 | Страница «ЗИП» — панели по отделам с фильтром (задача владельца №15) | 3ч |
| T-4-011 | Страница истории (`/displays/:slug/activity`) — единая лента (задача владельца №11) | 2ч |
| T-4-012 | Модалки: перемещение панели, смена состояния, создание заявки, archive | 3ч |
| T-4-013 | Hover-превью заявки (задача владельца №1) | 1ч |
| T-4-014 | Clamped comment с expand on hover (задача владельца №2) | 1ч |
| T-4-015 | Кнопка «История заявок» (задача владельца №3) — уже есть в API | 0.5ч |
| T-4-016 | Dropdown состояния панели в одну строку (задача владельца №5) | 0.5ч |
| T-4-017 | Вкладки комментов внутри модалки (задача владельца №6) | 1ч |
| T-4-018 | Форма экрана (DisplaySpec) на странице экрана (задача владельца №∞) | 2ч |
| T-4-019 | Tests: vitest + RTL для ключевых компонентов | 3ч |

### Backend остатки

| ID | Задача | Время |
|----|--------|-------|
| T-4-100 | Отключить Django templates (удалить templates/, старые views) | 1.5ч |
| T-4-101 | Nginx prod-конфиг: SPA + API + media | 2ч |
| T-4-102 | Production build frontend → static serving | 1ч |

**Выход фазы 4:**
- `/` открывает React SPA
- Админ-панель Django по-прежнему доступна на `/admin/`
- Старые Django templates удалены

---

## Фаза 5. Integrations (уведомления, MAX, Gmail)

**Цель:** починить уведомления, добавить МАХ, обойти блокировку TG.

**Продолжительность:** ~15 часов. Может идти параллельно с фазой 4.

| ID | Задача | Время |
|----|--------|-------|
| T-5-001 | Notification + NotificationPreference модели, админка | 2ч |
| T-5-002 | Перевод очереди с PubSub на Redis Streams + consumer group | 3ч |
| T-5-003 | Абстракция `NotificationChannel`, адаптер `TelegramChannel` | 2ч |
| T-5-004 | SOCKS5 proxy для TG (aiohttp + aiohttp-socks), env-конфиг | 1.5ч |
| T-5-005 | Адаптер `MaxChannel` (HTTP API МАХ), клон TG-логики | 2.5ч |
| T-5-006 | Бот в МАХ: базовая обработка команд `/start`, получение chat_id | 2ч |
| T-5-007 | Health-monitor: systemd unit + healthcheck endpoint + retry | 1ч |
| T-5-008 | Миграция Gmail парсера в `apps/integrations/gmail/` + тесты парсера | 1ч |

**Выход фазы 5:**
- Уведомления гарантированно доставляются
- При падении TG (РФ) автоматически шлёт через МАХ
- Панель «лога уведомлений» в админке

---

## После roadmap: long-tail задачи

Не обязательные, но полезные после выхода в прод:

- **Мониторинг:** django-prometheus + Grafana dashboard
- **Backups:** pgBackRest или WAL-G
- **Документация пользователя:** `docs.mstechnics.ru`
- **Импорт/экспорт:** CSV экспорт истории, импорт контактов
- **Мобильная адаптация:** PWA + офлайн-режим для техников на объектах
- **Push-уведомления:** webpush-api через PWA
- **Multi-language:** if когда-нибудь выйдет на зарубеж

---

## Что вне roadmap

Эти задачи **не входят** в план рефакторинга. Если владелец запросит — отдельный проект:

- Аналитика («сколько заявок в месяц по экрану X»)
- Планирование ТО
- Интеграция с внутренней бухгалтерией
- Мобильное нативное приложение

---

## Как следить за прогрессом

- Каждая задача в `ai-docs/03-tasks/` имеет статус: `ready / in-progress / review / done`
- Отчёты по закрытым задачам — `ai-docs/08-reports/<task-id>.md`
- Общий дашборд прогресса — `ai-docs/02-roadmap/progress.md` (ведёт архитектор)
