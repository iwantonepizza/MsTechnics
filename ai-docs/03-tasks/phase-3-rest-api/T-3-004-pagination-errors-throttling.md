# T-3-004. Pagination, error format, throttling

> **Тип:** infra
> **Приоритет:** P0
> **Оценка:** 1.5 часа
> **Фаза:** 3
> **Статус:** done

---

## Цель

Стандартизировать 3 кросс-режутых аспекта API: пагинацию, формат ошибок, лимит запросов. Один раз — все view'ы используют.

---

## Зависимости

- **Блокируется:** T-3-001
- **Блокирует:** все CRUD-задачи

---

## Что нужно сделать

### Шаг 1. Pagination — `shared/pagination.py`

Cursor-based по `api-conventions.md`:

```python
from base64 import urlsafe_b64encode, urlsafe_b64decode
import json

from rest_framework.pagination import CursorPagination as DRFCursorPagination
from rest_framework.response import Response


class CursorPagination(DRFCursorPagination):
    """
    Cursor-based пагинация, формат ответа по api-contract.md.
    
    Response:
        {
            "results": [...],
            "next_cursor": "<base64>" | null,
            "prev_cursor": "<base64>" | null,
            "has_more": bool
        }
    """
    page_size = 50
    page_size_query_param = 'limit'
    max_page_size = 200
    cursor_query_param = 'cursor'
    ordering = '-id'  # default; ViewSet может переопределить
    
    def get_paginated_response(self, data):
        return Response({
            'results': data,
            'next_cursor': self._get_cursor_from_url(self.get_next_link()),
            'prev_cursor': self._get_cursor_from_url(self.get_previous_link()),
            'has_more': self.has_next,
        })
    
    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'properties': {
                'results': schema,
                'next_cursor': {'type': 'string', 'nullable': True},
                'prev_cursor': {'type': 'string', 'nullable': True},
                'has_more': {'type': 'boolean'},
            },
        }
    
    @staticmethod
    def _get_cursor_from_url(url: str | None) -> str | None:
        """Извлекает значение ?cursor= из next/prev URL."""
        if not url:
            return None
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(url).query)
        return qs.get('cursor', [None])[0]
```

Прописать как default в `config/settings.py` (если ещё нет):

```python
REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS'] = 'shared.pagination.CursorPagination'
```

### Шаг 2. Error format — `shared/exceptions.py` extend

Уже есть `shared/exceptions.py` с `DomainError` (Фаза 2). Расширяем:

```python
# к существующему shared/exceptions.py добавить:

from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status as http_status


class DomainError(Exception):
    """Базовая ошибка доменной логики (уже существует)."""
    code: str = 'domain_error'
    http_status: int = http_status.HTTP_400_BAD_REQUEST
    
    def __init__(self, message: str | None = None, **kwargs):
        self.message = message or self.__class__.__doc__ or 'Domain error'
        self.context = kwargs
        super().__init__(self.message)


class InvalidStateTransition(DomainError):
    """Запрошенный переход состояния недопустим."""
    code = 'invalid_state_transition'
    http_status = http_status.HTTP_409_CONFLICT


class PanelHasActiveApplication(DomainError):
    """У панели есть активная заявка."""
    code = 'panel_has_active_application'
    http_status = http_status.HTTP_409_CONFLICT


class PermissionDeniedForCity(DomainError):
    """Нет доступа к этому городу."""
    code = 'forbidden_for_city'
    http_status = http_status.HTTP_403_FORBIDDEN


class PermissionDeniedForDepartment(DomainError):
    """Нет доступа для этой роли."""
    code = 'forbidden_for_department'
    http_status = http_status.HTTP_403_FORBIDDEN


class ConcurrentModification(DomainError):
    """Запись изменена параллельно."""
    code = 'concurrent_modification'
    http_status = http_status.HTTP_409_CONFLICT


def custom_exception_handler(exc, context):
    """
    Кастомный exception handler для DRF.
    
    Формат ошибки:
        {
            "detail": "Текст для пользователя",
            "code": "machine_readable_code",
            "errors": {field: [messages]} | null
        }
    """
    # 1. Доменные ошибки
    if isinstance(exc, DomainError):
        return Response(
            {
                'detail': exc.message,
                'code': exc.code,
                'errors': None,
            },
            status=exc.http_status,
        )
    
    # 2. DRF ValidationError → 422 + errors dict
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    
    # Для ValidationError DRF возвращает dict — переделываем в наш формат
    from rest_framework.exceptions import ValidationError
    if isinstance(exc, ValidationError):
        return Response(
            {
                'detail': 'Ошибка валидации',
                'code': 'validation_error',
                'errors': response.data if isinstance(response.data, dict) else None,
            },
            status=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    
    # Остальное — извлекаем стандартный detail
    detail = response.data.get('detail') if isinstance(response.data, dict) else str(response.data)
    code = response.data.get('code') if isinstance(response.data, dict) else None
    
    response.data = {
        'detail': detail or 'Произошла ошибка',
        'code': code or _code_from_status(response.status_code),
        'errors': None,
    }
    return response


def _code_from_status(status_code: int) -> str:
    return {
        400: 'bad_request',
        401: 'unauthorized',
        403: 'forbidden',
        404: 'not_found',
        405: 'method_not_allowed',
        409: 'conflict',
        422: 'validation_error',
        429: 'rate_limited',
    }.get(status_code, 'error')
```

В `config/settings.py`:

```python
REST_FRAMEWORK['EXCEPTION_HANDLER'] = 'shared.exceptions.custom_exception_handler'
```

### Шаг 3. Throttling — `shared/throttling.py`

```python
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class BurstRateThrottle(UserRateThrottle):
    """Защита от burst-ов — например, кнопка спам-нажимается."""
    scope = 'burst'


class SustainedRateThrottle(UserRateThrottle):
    """Долгий лимит — защита от auto-ботов."""
    scope = 'sustained'


class LoginRateThrottle(AnonRateThrottle):
    """Жёсткий лимит на login (защита от brute-force)."""
    scope = 'login'


class TransitionRateThrottle(UserRateThrottle):
    """Лимит на критичные state-transitions (защита от race condition двойных кликов)."""
    scope = 'transition'
```

В `config/settings.py`:

```python
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon':       '100/hour',
    'user':       '2000/hour',
    'burst':      '60/min',       # burst — 1 в секунду в среднем
    'sustained':  '5000/day',
    'login':      '10/min',       # 10 попыток входа в минуту с одного IP
    'transition': '120/min',      # 2 transitions в секунду — это много
}
```

### Шаг 4. Тесты

`apps/interface/tests/test_pagination.py`:

```python
import pytest
from rest_framework.test import APIRequestFactory

# Минимальный test ViewSet, чтобы проверить response shape
# (полный тест ViewSet'ов будет в задачах CRUD)

pytestmark = pytest.mark.django_db


def test_pagination_response_shape(api_client, panels_factory):
    """Создаём 100 панелей, ожидаем результат страницами по 50."""
    panels_factory.create_batch(100)
    
    # Сделать первый GET (когда T-3-021 готов):
    # response = api_client.get('/api/v1/panels/')
    # assert response.status_code == 200
    # assert 'results' in response.data
    # assert 'next_cursor' in response.data
    # assert 'has_more' in response.data
    # assert len(response.data['results']) == 50
    # assert response.data['has_more'] is True
    pass  # реальный тест после T-3-021
```

`tests/test_error_format.py`:

```python
import pytest

pytestmark = pytest.mark.django_db


def test_domain_error_returns_proper_format(api_client, ms_user_factory, application_factory):
    """Domain-error → JSON в нашем формате."""
    # После T-3-031:
    # user = ms_user_factory(permission='control')
    # api_client.force_authenticate(user=user)
    # 
    # app = application_factory(status__name='archive_done')
    # response = api_client.post(
    #     f'/api/v1/applications/{app.id}/transition/',
    #     {'target_state': 'apply_in_control'},
    # )
    # 
    # assert response.status_code == 409
    # assert response.data['code'] == 'invalid_state_transition'
    # assert 'detail' in response.data
    # assert response.data['errors'] is None
    pass


def test_validation_error_returns_422(api_client, ms_user_factory):
    """422 + errors dict при невалидном payload."""
    # После T-3-010:
    # response = api_client.post('/api/v1/auth/login/', {})  # пусто
    # assert response.status_code == 422
    # assert response.data['code'] == 'validation_error'
    # assert 'username' in response.data['errors']
    # assert 'password' in response.data['errors']
    pass
```

---

## Критерии приёмки

- [ ] `shared/pagination.py` — `CursorPagination` с правильной shape ответа
- [ ] `shared/exceptions.py` — `custom_exception_handler` обрабатывает `DomainError` и DRF ошибки
- [ ] `shared/throttling.py` — 4 scope-класса
- [ ] `REST_FRAMEWORK.DEFAULT_PAGINATION_CLASS` = `shared.pagination.CursorPagination`
- [ ] `REST_FRAMEWORK.EXCEPTION_HANDLER` = `shared.exceptions.custom_exception_handler`
- [ ] `REST_FRAMEWORK.DEFAULT_THROTTLE_RATES` содержит все 6 scope'ов
- [ ] Все ошибки приведены к формату `{detail, code, errors}`
- [ ] Тесты на pagination shape, error format, throttling — каркас (полные после CRUD)
- [ ] OpenAPI schema показывает правильную shape пагинации в response

---

## Что НЕ делать

- **НЕ используй** `LimitOffsetPagination` — для логов с большим количеством записей deep paging убивает БД
- **НЕ возвращай** plain text errors из DRF — всегда JSON
- **НЕ кеширу** throttle вне Redis (default django cache) — иначе локально не работает

---

## Smoke-test после Шага 1

После T-3-010 (logи) — попытка входа с пустым телом:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' -d '{}'

# Ожидаемый JSON:
{
  "detail": "Ошибка валидации",
  "code": "validation_error",
  "errors": {
    "username": ["This field is required."],
    "password": ["This field is required."]
  }
}
```
