# API Contract — REST v1

Контракт между backend (Django/DRF) и frontend (React SPA).

**Версионирование:** `/api/v1/`. Breaking changes → `/api/v2/` параллельно 1 месяц минимум.

**Аутентификация:** JWT через SimpleJWT.
- `Authorization: Bearer <access>`
- Access живёт 15 минут, refresh — 7 дней
- Refresh хранится в httpOnly Secure SameSite=Lax cookie

**Ответы:** JSON. Ошибки — JSON вида `{ "detail": "...", "code": "...", "errors": {...} }`.

**Пагинация:** cursor-based. `?cursor=<base64>&limit=50`. Default limit = 50, max = 200.

**Фильтрация:** query-params. Примеры: `?department=service&condition=problem`.

---

## 1. Аутентификация

```
POST   /api/v1/auth/login         { username, password } → 200 { access, refresh_set_in_cookie }
POST   /api/v1/auth/refresh       → 200 { access }                 (refresh из cookie)
POST   /api/v1/auth/logout        → 204                            (revoke refresh)
GET    /api/v1/me                 → 200 { id, username, email, permission, allowed_cities: [...], telegram_id, max_chat_id }
PATCH  /api/v1/me                 { telegram_id?, max_chat_id?, email? } → 200 { ... }
POST   /api/v1/me/change-password { old_password, new_password }   → 204
```

---

## 2. Справочники (core)

```
GET    /api/v1/cities                                    → [{ id, name, slug, timezone }]
GET    /api/v1/colors                                    → [{ id, name, hex }]
GET    /api/v1/icons                                     → [{ id, name, unicode_symbol }]
GET    /api/v1/conditions                                → [{ id, name, description, icon, color, allowed_transitions: [...] }]
GET    /api/v1/departments                               → [{ id, name, description }]
GET    /api/v1/application-statuses                      → [{ id, name, description, color, color_text, next_possible: [...] }]
GET    /api/v1/executors?city=<id>                       → [{ id, username, phone, telegram_id }]
```

---

## 3. Экраны (directory)

```
GET    /api/v1/displays?city=<slug>                      → [{ id, name, description, slug, city, rows, cols, current_condition, application_count }]
GET    /api/v1/displays/<slug>                           → full Display with cells and panels
GET    /api/v1/displays/<slug>/contacts                  → [{ id, name, phone, email, role }]
GET    /api/v1/displays/<slug>/photos                    → [{ id, url, uploaded_at, uploaded_by }]
POST   /api/v1/displays/<slug>/photos  (multipart)       → 201 { id, url }
DELETE /api/v1/displays/<slug>/photos/<id>               → 204
POST   /api/v1/displays/<slug>/assets/schematic (multipart file) → 200 Display
POST   /api/v1/displays/<slug>/assets/project   (multipart file) → 200 Display
```

`file_url`, `project_photo_url` и `photos[].url` возвращаются как `null`, если файл отсутствует
в storage. Клиент не должен показывать кнопку скачивания для `null`.

Загрузка assets принимает PDF или изображение до 10 МБ. Backend проверяет MIME и сигнатуру файла.

**Структура Display (GET detail):**
```json
{
  "id": 12,
  "name": "izhevsk-central",
  "description": "Центр, ул. Ленина 23",
  "slug": "izhevsk-central",
  "city": { "id": 1, "name": "Ижевск", "slug": "izhevsk" },
  "rows": 10,
  "cols": 10,
  "current_condition": { "id": 3, "name": "work", "icon": "✅", "color": { "hex": "#1ab11a" } },
  "file_url": "/media/schemes/izh-1.pdf",
  "project_photo_url": null,
  "cells": [
    {
      "id": 101,
      "position": "01",
      "row": 0,
      "col": 0,
      "panel": {
        "id": "P-12345",
        "condition": { "name": "work", "icon": "✅", "description": "Рабочая" },
        "application_status": { "name": "default", "color": { "hex": "#888" }, "color_text": { "hex": "#fff" } },
        "comment": "Заменена 2025-03-15"
      }
    },
    { "id": 102, "position": "02", "row": 0, "col": 1, "panel": null },
    ...
  ]
}
```

---

## 4. Панели (directory)

```
GET    /api/v1/panels?display=<slug>&department=<name>&condition=<name>  → [{ ... }]
GET    /api/v1/panels/<id>                                              → full Panel
PATCH  /api/v1/panels/<id>                   { comment?, condition_id? } → 200 { ... }
POST   /api/v1/panels/<id>/move-to-cell      { cell_id, comment? }       → 200
POST   /api/v1/panels/<id>/remove-from-cell  { comment?, condition_id? } → 200
POST   /api/v1/panels/<id>/change-department { department, comment? }    → 200
                                                                          (блокируется если есть активная заявка — #8)
GET    /api/v1/panels/<id>/history?kind=<moving|condition|breakdown|service|none_type&since=...> → [{ ... }]
GET    /api/v1/panels/<id>/applications?status=<...>                     → [{ ... }]
```

---

## 5. ZIP модули

```
GET    /api/v1/zip/lamels?display=<slug>    → [{ id, name, count, display, comment }]
GET    /api/v1/zip/hubs?display=<slug>
GET    /api/v1/zip/wires?display=<slug>
PATCH  /api/v1/zip/<kind>/<id>              { count?, comment? }
POST   /api/v1/zip/<kind>/<id>/photo (multipart)
DELETE /api/v1/zip/<kind>/<id>/photo/<photo_id>
```

---

## 6. Заявки (workflow)

```
GET    /api/v1/applications?display=<slug>&box=<name>&cell=<pos>&panel=<id>  
       → cursor-paginated [{ ... }]
       (box: received, at_work, complete, done, archive, unable, application_history, all)

GET    /api/v1/applications/<id>              → full Application with events

POST   /api/v1/applications                   { panel_id, cell_id, display_id, comment, file? (multipart) }
                                               → 201 { ... }
POST   /api/v1/applications/<id>/transition   { target_state, comment?, executor_id?, file? } → 200 { ... }
DELETE /api/v1/applications/<id>              (только для sent_to_control от создателя, в окно 5 минут) → 204
GET    /api/v1/applications/<id>/events       → [{ id, event_type, user, timestamp, comment, file, state_from, state_to }]
```

**Структура Application (GET detail):**
```json
{
  "id": 4567,
  "status": { "id": 3, "name": "sent_to_service", "description": "Отправлена в сервис",
              "color": { "hex": "#ffa500" }, "color_text": { "hex": "#000" } },
  "display": { "id": 12, "slug": "izhevsk-central", "description": "..." },
  "panel": { "id": "P-12345" },
  "cell": { "id": 101, "position": "03" },
  "executor": { "id": 5, "username": "artem" },
  "last_update_date_time": "2025-04-22T10:23:15+03:00",
  "created_at": "2025-04-20T09:00:00+03:00",
  "events": [
    { "event_type": "created",         "state_from": null,                   "state_to": "sent_to_control",
      "user": "katya",  "timestamp": "2025-04-20T09:00:00+03:00",
      "comment": "Панель моргает", "file": "/media/apps/4567/1.jpg" },
    { "event_type": "control_applied", "state_from": "sent_to_control",       "state_to": "apply_in_control",
      "user": "misha",  "timestamp": "2025-04-20T09:30:00+03:00", "comment": null, "file": null },
    { "event_type": "sent_to_service", "state_from": "apply_in_control",      "state_to": "sent_to_service",
      "user": "misha",  "timestamp": "2025-04-20T09:32:00+03:00", "comment": "Срочно" }
  ]
}
```

**Transitions (`POST /api/v1/applications/<id>/transition`):**

| target_state      | from_state        | allowed_for    | required              |
|-------------------|-------------------|----------------|-----------------------|
| apply_in_control  | sent_to_control   | control        | -                     |
| sent_to_service   | apply_in_control  | control        | -                     |
| work_in_service   | sent_to_service   | service        | executor_id?          |
| done              | work_in_service   | service        | -                     |
| unable            | work_in_service   | service        | comment (required)    |
| archive_done      | done              | control/service| -                     |
| archive_unable    | unable            | control/service| -                     |

---

## 7. Выезды (workflow)

```
GET    /api/v1/departures?status=<...>&city=<id>       → [{ ... }]
POST   /api/v1/departures                { description, city_id, executor_id?, time_start? } → 201
PATCH  /api/v1/departures/<id>           { executor_id?, time_start?, description? } → 200
POST   /api/v1/departures/<id>/complete  { comment?, time_end? } → 200
POST   /api/v1/departures/<id>/archive                            → 200
DELETE /api/v1/departures/<id>                                    → 204 (только status=created)
```

---

## 8. Журнал активности (activity)

```
GET    /api/v1/activity-log?display=<slug>&panel=<id>&cell=<id>&kind=<...>&event_types=<csv>&feed=true&cursor=<cursor>&limit=<n>
       → cursor-paginated [{ id, event_type, target_kind, target_id, user, timestamp, comment, file, payload }]
       
       kind: panel-condition, panel-moving, panel-breakdown, panel-service, application-created,
             application-transition, display-note, cell-note, monitoring-report, ...
```

Единый endpoint для всех историй (задача владельца #11).
Для owner UX ленты и истории по умолчанию показываются за всё время; ограничение по `since`
используется только если экран явно вводит временной фильтр.

---

## 9. Дашборд и сводки

```
GET    /api/v1/dashboard                 → { monitoring, control, service, zip, departures } — по правам юзера

GET    /api/v1/reports/panels?city=<id>&since=...    → [{ ... }]    (существующие panel_reports)
GET    /api/v1/reports/service?city=<id>&since=...   → [{ ... }]    (существующие panel_service_report)
```

---

## 10. Уведомления

```
GET    /api/v1/notifications?unread=true&limit=50
POST   /api/v1/notifications/<id>/read
POST   /api/v1/notifications/read-all
```

**Real-time через SSE:**
```
GET    /api/v1/events/stream                        → text/event-stream
       на каждое событие:
       event: application.transition
       data: {"application_id": 4567, "state_from": "sent_to_service", "state_to": "work_in_service", "display_slug": "izhevsk-central"}
```

---

## 11. Специфика полей

### Dates
Все даты — ISO 8601 с таймзоной: `"2025-04-22T10:23:15+03:00"`. Таймзона — пользователя (или города, если контекст есть).

### IDs
- Целочисленные ID — для всего, что Django-модель: `cell.id`, `application.id`, `user.id`.
- Панели — строковые: `"P-12345"` — поле `Panel.name` в БД, используется как PK после миграции.
- Display.slug — для URL; display.id — для API.
- City.slug — для URL; city.id — для API.

### Цвета
Всегда как `{ "id": 5, "name": "amber", "hex": "#ffa500" }`. Не передаём голый hex.

### Статусы
Всегда как `{ "id": 3, "name": "sent_to_service", "description": "Отправлена в сервис" }`.

### Файлы
Все файлы — через URL. Загрузка — `multipart/form-data`.

---

## 12. Правила ошибок

```json
{
  "detail": "Нельзя перевести панель с активной заявкой",
  "code": "panel_has_active_application",
  "errors": null
}
```

- `detail` — человекочитаемое сообщение (на русском)
- `code` — машиночитаемый код ошибки (для i18n клиента и логирования)
- `errors` — словарь поле→ошибки при 422, иначе null

### Коды
- `invalid_credentials` — 401 при логине
- `token_expired` — 401 — клиент должен перерелогиниться
- `forbidden_for_role` — 403
- `forbidden_for_city` — 403
- `validation_error` — 422
- `panel_has_active_application` — 409 — задача владельца #8
- `invalid_state_transition` — 409
- `concurrent_modification` — 409 — запись изменена параллельно
- `rate_limited` — 429

---

## 13. Правила безопасности

- `allowed_city`-фильтрация **всегда** на бэке; клиент не должен полагаться, что ему не пришлют чужой город
- `permission`-проверка **всегда** на бэке; клиент скрывает UI, но это только UX
- Все state-изменяющие эндпоинты требуют CSRF-токен + JWT. SSE работает по короткоживущему токену в query-параметре
- Загрузка файлов — валидация MIME, лимит 10MB, магические байты
- Upload-пути — через UUID, не по username

---

## 14. Правила клиента (React)

- **Все запросы через TanStack Query.** Не голый fetch.
- **QueryKey структурирован:** `['applications', { display, box, cell }]`.
- **Mutations всегда invalidate соответствующие queries.**
- **401 → refresh → retry 1 раз →** если упало — logout.
- **Retry на 5xx — 2 раза с экспоненциальным бэк-оффом.** Не на мутациях.
- **Timeout — 15 секунд** для всего. Больше — запрос долже переделываться через очередь.

---

## 15. Этот контракт

**Живой.** Меняется только через PR с апдейтом этого файла и миграцией от старого эндпоинта к новому. Любое breaking change → через `/api/v2/` или deprecation-warning в хедерах минимум 2 недели.

Ответственный за контракт — архитектор. Любая попытка FE или BE изменить форму ответа без апдейта этого файла — отклоняется на ревью.
