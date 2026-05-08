# Целевая архитектура MsTechnics

Это конечная точка, к которой мы движемся рефакторингом. Код, который противоречит этому документу, — технический долг и подлежит переделке.

---

## 1. Базовые принципы

### Принцип 1. Чистое разделение слоёв

Зависимости идут **только сверху вниз** по следующей иерархии. Нарушение — блокер PR.

```
┌──────────────────────────────────────────────────────┐
│ interface/   ← REST API views, DRF serializers        │
│   ↓ зависит от services                               │
├──────────────────────────────────────────────────────┤
│ workflow/    ← заявки, выезды, задания                │
│   ↓ зависит от directory, core                        │
├──────────────────────────────────────────────────────┤
│ directory/   ← каталог железа: экраны, панели, ячейки │
│   ↓ зависит от core                                   │
├──────────────────────────────────────────────────────┤
│ integrations/← внешние: TG, МАХ, Gmail, VNNOX          │
│   ↓ зависит от core                                   │
├──────────────────────────────────────────────────────┤
│ core/        ← цвета, иконки, города, пользователи    │
│   базовый слой, ни от чего не зависит                 │
└──────────────────────────────────────────────────────┘
```

**Правило:** `core` не знает про `directory`. `directory` не знает про `workflow`. И так далее. Обратные зависимости запрещены.

### Принцип 2. Thin views, fat services

Контроллеры (DRF views) — только:

1. Получение данных из запроса
2. Проверка прав (через `permission_classes`)
3. Вызов сервиса
4. Сериализация результата

**Всё остальное** — в `services/` или `use_cases/`. Никакой бизнес-логики в views.

### Принцип 3. Models are dumb, services are smart

Модели Django — это **схема БД + базовые инварианты** (constraints, `clean()`).
Бизнес-логика в моделях (`save()` с побочными эффектами, как сейчас в `Display.save`) — **запрещена**.

Если нужно создать экран с ячейками и панелями — это делает `DisplayFactory.create()`, не `Display.save()`.

### Принцип 4. FSM — это объект

Переходы статусов заявки — не 8 веток `if` в 150-строчной функции, а `ApplicationStateMachine` с декларативным набором `Transition` и методом `transition(application, target)`, валидирующим допустимость перехода.

### Принцип 5. События — first-class

Каждое значимое действие (создание заявки, перемещение панели, смена состояния) = событие в `ActivityLog`. Единая таблица с `ContentType` + `GenericForeignKey` + `event_type`.

Это даёт пользователю «все действия по экрану в одном месте» бесплатно — фильтрация по target_object.

### Принцип 6. Никакой синхронной отправки в TG/MAX

Вью **никогда** не вызывает `async_to_sync(send_telegram)`. Вместо этого — `notification_queue.enqueue(event)`. Worker разгребает.

### Принцип 7. Всё, что не модель и не сервис, — либо tests, либо infra

Утилиты класса «скрипт запускается отдельно» (`daily_checker.py`, `ManageControl.py`) живут в `bin/` или `services/management/commands/` (как Django management commands).

---

## 2. Структура репозитория (целевая)

```
mstechnics/
├── AGENTS.md
├── README.md
├── pyproject.toml              ← replacement для requirements.txt
├── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── .env.example
├── .pre-commit-config.yaml
├── .github/
│   └── workflows/
│       ├── ci.yml              ← ruff + black + mypy + pytest
│       └── cd.yml              ← deploy on main
│
├── ai-docs/                    ← вся документация проекта
│
├── backend/
│   ├── manage.py
│   ├── config/                 ← бывший MsServiceControl/
│   │   ├── __init__.py
│   │   ├── settings/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── dev.py
│   │   │   ├── prod.py
│   │   │   └── test.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   │
│   ├── apps/
│   │   ├── core/               ← цвета, иконки, города, пользователи
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── city.py
│   │   │   │   ├── color.py
│   │   │   │   ├── icon.py
│   │   │   │   └── user.py
│   │   │   ├── services/
│   │   │   ├── api/
│   │   │   │   ├── serializers.py
│   │   │   │   ├── views.py
│   │   │   │   └── urls.py
│   │   │   ├── admin.py
│   │   │   └── tests/
│   │   │
│   │   ├── directory/          ← экраны, панели, ячейки, отделы, состояния
│   │   │   ├── models/
│   │   │   │   ├── display.py
│   │   │   │   ├── panel.py
│   │   │   │   ├── cell.py
│   │   │   │   ├── department.py
│   │   │   │   ├── condition.py
│   │   │   │   └── storage.py       ← Wires, Hubs, Lamels
│   │   │   ├── services/
│   │   │   │   ├── display_factory.py
│   │   │   │   └── panel_mover.py
│   │   │   ├── api/
│   │   │   └── tests/
│   │   │
│   │   ├── workflow/           ← заявки, выезды, задания
│   │   │   ├── applications/
│   │   │   │   ├── models.py
│   │   │   │   ├── fsm.py           ← ApplicationStateMachine
│   │   │   │   ├── services.py
│   │   │   │   ├── api/
│   │   │   │   └── tests/
│   │   │   ├── departures/
│   │   │   └── daily_tasks/
│   │   │
│   │   ├── activity/           ← единый ActivityLog
│   │   │   ├── models.py            ← ActivityLog (один на всех)
│   │   │   ├── services.py          ← log_event(actor, target, type, ...)
│   │   │   ├── signals.py
│   │   │   ├── api/
│   │   │   └── tests/
│   │   │
│   │   ├── notifications/      ← единая подсистема уведомлений
│   │   │   ├── models.py            ← Notification, NotificationChannel
│   │   │   ├── channels/
│   │   │   │   ├── base.py          ← abstract NotificationChannel
│   │   │   │   ├── telegram.py      ← TelegramChannel (через proxy)
│   │   │   │   ├── max_chat.py      ← MaxChannel
│   │   │   │   └── stub.py          ← для тестов
│   │   │   ├── queue.py             ← Redis Streams producer/consumer
│   │   │   ├── worker.py            ← entrypoint для воркера
│   │   │   ├── services.py
│   │   │   └── tests/
│   │   │
│   │   ├── integrations/       ← внешние источники данных
│   │   │   ├── gmail/               ← парсинг писем VNNOX
│   │   │   │   ├── client.py
│   │   │   │   ├── parser.py
│   │   │   │   ├── models.py
│   │   │   │   └── tasks.py         ← management command
│   │   │   └── health/              ← бывший ManageControl.py
│   │   │       └── worker.py
│   │   │
│   │   └── interface/          ← легаси API-эндпоинты (v1), тонкие фасады
│   │       └── api/
│   │
│   ├── shared/                 ← общее: exceptions, types, utils
│   │   ├── exceptions.py
│   │   ├── logging.py
│   │   └── time.py             ← бывший get_time.py
│   │
│   └── tests/
│       ├── conftest.py
│       ├── factories.py        ← factory_boy
│       └── e2e/
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── routes/
│       ├── pages/
│       │   ├── LoginPage/
│       │   ├── MainMenuPage/
│       │   ├── MonitoringPage/
│       │   ├── ControlPage/
│       │   ├── ServicePage/
│       │   ├── ZipPage/
│       │   └── ActivityLogPage/
│       ├── features/           ← feature-based разбивка
│       │   ├── applications/
│       │   ├── panels/
│       │   ├── departures/
│       │   └── notifications/
│       ├── entities/           ← модели домена (types)
│       ├── shared/             ← компоненты, хуки, утилиты
│       │   ├── ui/             ← shadcn/ui + кастомные
│       │   ├── api/            ← axios + TanStack Query
│       │   ├── lib/
│       │   └── hooks/
│       └── styles/
│
├── infra/
│   ├── nginx/
│   │   └── nginx.conf
│   ├── systemd/
│   │   ├── mstechnics-web.service
│   │   ├── mstechnics-notifications-worker.service
│   │   ├── mstechnics-daily-checker.service
│   │   └── mstechnics-health-monitor.service
│   └── scripts/
│       ├── backup-db.sh
│       └── restore-db.sh
│
└── scripts/                    ← dev-скрипты
    ├── bootstrap.sh
    └── seed-demo-data.py
```

---

## 3. Ключевые изменения моделей

### 3.1 Денормализация Application

**Было** (28 полей на одну таблицу):

```python
class Application:
    comment_monitoring, time_monitoring, file_monitoring, user_monitoring
    comment_control_apply, time_control_apply, ...
    comment_control_send, ...
    comment_service_apply, ...
    ... ещё 5 раз
```

**Стало:**

```python
class Application:
    id: int
    display: FK(Display)
    panel: FK(Panel)
    cell: FK(Cell)
    status: FK(ApplicationStatus)
    executor: FK(Executor, null=True)
    created_at: DateTime
    updated_at: DateTime

class ApplicationEvent:
    application: FK(Application)
    stage: CharField  # monitoring_create, control_apply, control_send, etc.
    comment: TextField
    file: FileField
    actor: FK(User)
    occurred_at: DateTime
```

Все «комменты каждого этапа» получаются через `application.events.filter(stage='...')`.

### 3.2 Единый ActivityLog

**Было:** 5 таблиц-историй, почти идентичные.

**Стало:**

```python
class ActivityLog:
    actor: FK(User, null=True)
    target_type: FK(ContentType)       ← Panel / Display / Application / Departure
    target_id: int
    target: GenericForeignKey
    event_type: CharField                 ← move / breakdown / service / condition_change / etc.
    description: TextField
    comment: TextField
    payload: JSONField                    ← доп. контекст (from_department, to_department, ...)
    occurred_at: DateTime
    ip_address: GenericIPAddressField
```

Запрос «все действия по экрану X» = `ActivityLog.objects.for_target(display_x).order_by('-occurred_at')`.

### 3.3 FK по PK, не по name

**Было:**

```python
display = ForeignKey(Display, to_field='name')
```

**Стало:**

```python
display = ForeignKey(Display, on_delete=PROTECT)
```

`to_field='name'` мешает переименовать объект, увеличивает размер индекса, ломает миграции. Всё — через PK.

### 3.4 FSM-машина заявки

Объявляется декларативно:

```python
class ApplicationStateMachine:
    TRANSITIONS = [
        Transition(
            from_status='application_sent_to_control',
            to_status='application_apply_in_control',
            event_stage='control_apply',
            on_transition=[set_panel_condition_error],
            permission='control',
        ),
        # ... остальные
    ]

    def transition(self, application, target_status, actor, comment=None, file=None):
        # 1. ищет переход
        # 2. проверяет права actor
        # 3. создаёт ApplicationEvent
        # 4. сохраняет Application.status
        # 5. запускает on_transition хуки
        # 6. логирует в ActivityLog
        # 7. кидает в notification_queue
```

---

## 4. API (DRF)

### 4.1 Версионирование

```
/api/v1/
```

Все эндпоинты живут под `/api/v1/`. Изменения ломающие контракт → `/api/v2/`. Старый работает минимум 1 квартал.

### 4.2 Аутентификация

**SimpleJWT**:

- `POST /api/v1/auth/login/` → возвращает `access` + `refresh`
- `POST /api/v1/auth/refresh/`
- `POST /api/v1/auth/logout/` (через blacklist)

Фронт хранит `access` в памяти (не в localStorage!), `refresh` в HttpOnly cookie.

### 4.3 Структура URL

```
/api/v1/auth/
/api/v1/users/me/
/api/v1/cities/
/api/v1/displays/
/api/v1/displays/<slug>/panels/
/api/v1/panels/
/api/v1/panels/<id>/
/api/v1/panels/<id>/move/                     POST: сменить отдел
/api/v1/panels/<id>/condition/                POST: сменить состояние
/api/v1/cells/
/api/v1/applications/
/api/v1/applications/<id>/
/api/v1/applications/<id>/transitions/        GET: возможные переходы
/api/v1/applications/<id>/transition/         POST: выполнить переход
/api/v1/departures/
/api/v1/executors/
/api/v1/activity/                             ← ActivityLog endpoint
  ?target_type=display&target_id=42
  ?actor=<user_id>
  ?event_type=breakdown
/api/v1/storage/wires/
/api/v1/storage/hubs/
/api/v1/storage/lamels/
```

### 4.4 Формат ошибок

Единый формат (см. `04-conventions/api-conventions.md`):

```json
{
  "error": {
    "code": "APPLICATION_INVALID_TRANSITION",
    "message": "Нельзя перевести заявку из 'done' в 'application_sent_to_service'",
    "details": { "current_status": "done", "target_status": "application_sent_to_service" }
  }
}
```

---

## 5. Слой уведомлений (новый)

```
┌──────────────────┐       ┌─────────────────┐        ┌──────────────┐
│ Domain service   │──►    │ notification_   │───►    │ Redis Stream │
│ (любой)          │ enq   │ queue           │ xadd   │ `notifs:v1`  │
└──────────────────┘       └─────────────────┘        └──────┬───────┘
                                                             │ xreadgroup
                                                             ▼
                                                    ┌─────────────────┐
                                                    │ NotifWorker     │
                                                    │ (consumer group)│
                                                    └────┬───┬───┬────┘
                                                         │   │   │
                                           ┌─────────────┘   │   └────────────┐
                                           ▼                 ▼                ▼
                                   ┌─────────────┐    ┌──────────┐    ┌──────────┐
                                   │ Telegram    │    │ MAX      │    │ Email    │
                                   │ (socks5)    │    │ (HTTP)   │    │ fallback │
                                   └─────────────┘    └──────────┘    └──────────┘
```

Детали — в `06-integrations/notifications-redesign.md`.

---

## 6. Frontend (React SPA)

- Точка входа `/` — если не авторизован, редирект на `/login`.
- Разбивка роутов по ролям:
  - `/monitoring/*` — только `monitoring / all / admin`
  - `/control/*` — `control / all / admin`
  - `/service/*` — `service / all / admin`
  - `/zip/*` — `service / all / admin`
- Общие страницы:
  - `/menu` — главная с дашбордом отделов
  - `/displays/:slug/activity` — единая лента событий по экрану (**новый экран**)
  - `/profile` — ЛК
- State management:
  - **Server state** — TanStack Query (кэш, инвалидация, refetch)
  - **Client state** — Zustand (selected panel, filters, ui-state)
  - **Form state** — React Hook Form + zod

Детали — в `07-frontend/screens-map.md`.

---

## 7. Что удаляется

- `ConcreteMsUser` — мёртвый код
- `MsServiceControl/` → переименовать в `config/`
- `get_time.py` из корня → в `shared/time.py`
- `daily_checker.py`, `ManageControl.py`, `sender_tg_message.py` из корня → в `apps/*/worker.py`
- `sorting_message.py` из корня → в `apps/notifications/services.py`
- Все Django-templates после миграции фронта на SPA → в `legacy/` на время переходного периода, потом удалить

---

## 8. Что сохраняется (и почему)

- **PostgreSQL** — у нас уже есть данные, миграция в SQLite/MySQL = риск
- **Redis** — используется, работает
- **Django 5.1** — стабильная LTS-подобная версия
- **Python 3.12** — совместим со всем стеком
- Бизнес-логика заявок (**FSM**) — только реорганизуется, не меняется
- Модель `Display / Cell / Panel` — структура остаётся, меняются FK по name → FK по id

---

## 9. Итоговые контрольные вопросы, на которые должен уметь ответить архитектор через месяц

- Где проходит граница между `directory` и `workflow`? → там, где железо становится бизнес-процессом. Панель в `directory`. Заявка по панели — в `workflow`.
- Почему ActivityLog, а не оставить 5 таблиц? → DRY + фича «всё в одном месте» бесплатно.
- Почему не Celery? → есть работающий worker, Streams решают то же, минус зависимость.
- Почему REST, а не GraphQL? → команда маленькая, эндпоинты простые, оверхед GraphQL не оправдан.
- Почему JWT, а не sessions? → SPA на другом origin может быть, scaling-friendly.

Если ответ на один из этих вопросов изменится — создаётся ADR.
