# API Conventions

Правила, общие для всех REST-эндпоинтов. Если что-то противоречит этим правилам — сначала сюда правку, потом код.

---

## 1. Версионирование

- Путь: `/api/v1/...`
- Breaking changes → `v2` параллельно с `v1` минимум 1 месяц
- Non-breaking (добавили опциональное поле в response, новый эндпоинт) — добавляем в существующую версию

## 2. Пути

- **Существительные во множественном числе:** `/applications`, `/panels`, `/displays`
- **Иерархия — через вложенность:** `/displays/<slug>/cells/`
- **Действия — через sub-resource или POST с суффиксом:**
  - `POST /applications/<id>/transition` — transition
  - `POST /panels/<id>/remove-from-cell` — действие
  - Избегаем `POST /applications/transition?id=<id>` — менее RESTful

## 3. Методы

| Метод | Семантика |
|---|---|
| GET | чтение, идемпотентно, без body |
| POST | создание ИЛИ действие с побочным эффектом |
| PATCH | частичное обновление |
| PUT | не используем (вызывает путаницу) |
| DELETE | удаление; часто — soft delete |

## 4. Ответы

### Успех
- `200 OK` — чтение, успешное обновление
- `201 Created` — создание, обязательно `Location` header
- `204 No Content` — успех без тела (DELETE, некоторые PATCH)

### Ошибки клиента
- `400 Bad Request` — невалидный JSON, отсутствующие обязательные поля
- `401 Unauthorized` — нет/невалидный токен
- `403 Forbidden` — токен валиден, но доступа нет
- `404 Not Found` — ресурс не существует **или** принадлежит не вам (для предотвращения утечки существования)
- `409 Conflict` — конфликт состояний (FSM transition invalid, panel has active application)
- `422 Unprocessable Entity` — валидация не прошла
- `429 Too Many Requests` — rate limit

### Ошибки сервера
- `500 Internal Server Error` — баг
- `502 Bad Gateway` — upstream (Telegram, Gmail) не отвечает
- `503 Service Unavailable` — перегружены / в maintenance

## 5. Формат ошибки

```json
{
  "detail": "Нельзя перевести панель с активной заявкой",
  "code": "panel_has_active_application",
  "errors": null
}
```

`errors` — словарь `{ field_name: ["сообщение1", "сообщение2"] }` для 422:
```json
{
  "detail": "Validation failed",
  "code": "validation_error",
  "errors": {
    "comment": ["Обязательное поле"],
    "executor_id": ["Исполнитель не найден"]
  }
}
```

Список `code` — в `api-contract.md`.

## 6. Пагинация

- Cursor-based: `?cursor=<base64>&limit=50`
- Ответ:
  ```json
  {
    "results": [...],
    "next_cursor": "eyJvZmZzZXQiOjUwfQ==",
    "prev_cursor": null,
    "has_more": true
  }
  ```
- Default `limit=50`, max `limit=200`.

## 7. Фильтрация

- Query-params: `?display=izhevsk-central&condition=problem`
- Диапазоны: `?since=2025-01-01T00:00:00Z&before=2025-02-01T00:00:00Z`
- Булевы: `?is_active=true` (не `?is_active=1`)

## 8. Сортировка

- `?ordering=-created_at,+id`
- `-` в начале = desc
- Максимум 3 поля

## 9. Поля в ответе

- snake_case ключи (`created_at`, не `createdAt`)
- Даты — ISO 8601 с таймзоной: `"2025-04-22T10:23:15+03:00"`
- Null vs отсутствие поля: если значение может быть, но его нет — `"executor": null`. Если вообще не применимо — поле **отсутствует**.
- Вложенные объекты вместо ID:
  ```json
  // плохо:
  "executor_id": 5

  // хорошо:
  "executor": { "id": 5, "username": "artem" }
  ```
  Для записи — наоборот, принимаем `executor_id`.

## 10. Body входящих запросов

- `Content-Type: application/json` по умолчанию
- `multipart/form-data` для файлов
- snake_case
- Даты ISO 8601

## 11. Заголовки

Обязательные в каждом ответе:
- `X-Request-ID` — прокидывается из запроса или генерируется
- `X-API-Version` — `v1`

Обязательные в каждом запросе клиента:
- `Authorization: Bearer <access_token>` (кроме `/auth/login` и `/webhooks/*`)
- `Accept: application/json`

## 12. Security

- JWT в `Authorization` header, refresh — в `httpOnly Secure SameSite=Lax` cookie
- CSRF для mutations, которые ходят из SPA с cookie (или полностью JWT, без session — CSRF не нужен)
- Rate limits: см. конфиг DRF throttle
- CORS: только `FRONTEND_URL` из env

## 13. Идемпотентность

Для non-idempotent операций (POST создание) — клиент может передавать `Idempotency-Key` header. Сервер должен помнить его в Redis 24ч и возвращать тот же результат.

Пока не обязательно, но дизайним с возможностью добавить.

## 14. Версия как намёк deprecation

В response добавляем:
```
X-Deprecation: This endpoint will be removed in v2 (2025-09-01). Use /api/v2/applications/<id>/transition instead.
```

## 15. Спецификация

Автогенерация OpenAPI через `drf-spectacular`:
- Схема доступна: `/api/schema/`
- Swagger UI: `/api/docs/` (только в dev)
- Из OpenAPI генерим TS-типы для фронта

## 16. Тесты

- Каждый endpoint — минимум 3 теста: happy path, 403, 422
- Schema check: `test_openapi_schema_is_valid` в тестах
- Contract-тест: для критичных (login, transition) — фиксируем response-структуру snapshot'ом
