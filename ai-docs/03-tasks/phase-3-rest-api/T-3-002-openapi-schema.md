# T-3-002. OpenAPI schema через drf-spectacular

> **Тип:** infra
> **Приоритет:** P0
> **Оценка:** 1 час
> **Фаза:** 3
> **Статус:** done

---

## Цель

Автогенерируемая OpenAPI 3 схема. Из неё фронтенд генерирует TypeScript-типы (`pnpm generate:api-types`), архитектор делает contract-tests, новые разработчики читают Swagger.

---

## Зависимости

- **Блокируется:** T-3-001
- **Блокирует:** T-3-014 (TS-генерация для фронта), все остальные API-задачи лучше выполнять с этим — иначе schema "догоняет"

---

## Что нужно сделать

### Шаг 1. Settings

В `config/settings.py`:

```python
SPECTACULAR_SETTINGS = {
    'TITLE': 'MsTechnics API',
    'DESCRIPTION': 'REST API для системы управления LED-экранами.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,  # отдельные схемы для request/response
    'SCHEMA_PATH_PREFIX': r'/api/v[0-9]+',
    'SCHEMA_PATH_PREFIX_TRIM': False,
    'SORT_OPERATIONS': False,
    'AUTHENTICATION_WHITELIST': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'TAGS': [
        {'name': 'auth',          'description': 'Аутентификация'},
        {'name': 'me',            'description': 'Текущий пользователь'},
        {'name': 'refs',          'description': 'Справочники'},
        {'name': 'displays',      'description': 'Экраны'},
        {'name': 'panels',        'description': 'Панели'},
        {'name': 'cells',         'description': 'Ячейки'},
        {'name': 'storage',       'description': 'ЗИП-расходники'},
        {'name': 'applications',  'description': 'Заявки'},
        {'name': 'departures',    'description': 'Выезды'},
        {'name': 'activity',      'description': 'Журнал активности'},
        {'name': 'events',        'description': 'Real-time события (SSE)'},
        {'name': 'health',        'description': 'Health checks'},
    ],
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'displayOperationId': False,
        'docExpansion': 'none',
        'persistAuthorization': True,
    },
    'SERVERS': [
        {'url': 'http://localhost:8000', 'description': 'dev'},
        {'url': 'https://staging.mstechnics.ru', 'description': 'staging'},
        {'url': 'https://mstechnics.ru', 'description': 'prod'},
    ],
}
```

### Шаг 2. URLs

В `config/urls.py`:
```python
from drf_spectacular.views import (
    SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView,
)

urlpatterns += [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

В **prod** — `SpectacularSwaggerView` отключить (не светить документацию):

```python
# config/settings/prod.py
DEBUG = False

# Удалить swagger UI route'ы из urlpatterns в проде
```

Лучше сделать через условие в urls.py:
```python
if settings.DEBUG or settings.ENABLE_API_DOCS:
    urlpatterns += [path('api/docs/', ...)]
```

### Шаг 3. Декораторы для view'ов

Каждый view должен использовать `@extend_schema` или drf-spectacular будет угадывать (часто неточно).

Пример (для T-3-010 потом):
```python
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

class LoginView(APIView):
    @extend_schema(
        tags=['auth'],
        summary='Вход в систему',
        description='Возвращает access-токен и устанавливает refresh в httpOnly cookie.',
        request=LoginRequestSerializer,
        responses={
            200: OpenApiResponse(
                response=LoginResponseSerializer,
                description='Успешный вход',
            ),
            401: OpenApiResponse(description='Неверные учётные данные'),
        },
        examples=[
            OpenApiExample(
                'Login example',
                value={'username': 'misha', 'password': 'secret'},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        ...
```

### Шаг 4. Кастомные сериализаторы для ошибок

`shared/api_errors.py`:

```python
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers


def error_response(description: str = ''):
    """Стандартный формат ошибки для drf-spectacular."""
    return inline_serializer(
        name='ErrorResponse',
        fields={
            'detail': serializers.CharField(),
            'code': serializers.CharField(),
            'errors': serializers.JSONField(allow_null=True),
        },
    ), description
```

### Шаг 5. Команда экспорта

`apps/interface/management/commands/export_openapi.py`:

```python
from django.core.management.base import BaseCommand
from drf_spectacular.management.commands.spectacular import Command as SpectacularCommand


class Command(SpectacularCommand):
    """Wrapper над spectacular с дефолтами для нашего проекта."""
    help = 'Экспорт OpenAPI schema в файл api-schema.yaml'

    def handle(self, *args, **options):
        # Принудительно выводим в файл с предсказуемым именем
        options['file'] = 'api-schema.yaml'
        options['format'] = 'openapi'
        options['validate'] = True
        super().handle(*args, **options)
```

Использование:
```bash
python manage.py export_openapi
# создаёт api-schema.yaml в корне
```

### Шаг 6. CI-проверка

В `.github/workflows/ci.yml` добавить:
```yaml
- name: Validate OpenAPI schema
  run: |
    python manage.py spectacular --validate --file api-schema.yaml
```

Это ловит баги типа "забыл `serializer_class`" или "ошибка в `extend_schema`".

### Шаг 7. Smoke-test

После T-3-010 (когда будут реальные эндпоинты):

```bash
python manage.py runserver
# открыть http://localhost:8000/api/docs/
# должна быть Swagger UI со списком эндпоинтов

# Проверить контракт:
python manage.py spectacular --validate
# 0 errors

# Сравнить с api-contract.md (визуально):
# - все эндпоинты на месте?
# - формы request/response совпадают?
```

---

## Критерии приёмки

- [ ] `drf-spectacular` в зависимостях
- [ ] `SPECTACULAR_SETTINGS` в `config/settings.py`
- [ ] `/api/schema/` отдаёт OpenAPI YAML
- [ ] `/api/docs/` показывает Swagger UI (только в dev/staging)
- [ ] `/api/redoc/` показывает ReDoc (только в dev/staging)
- [ ] В prod docs НЕ доступны
- [ ] `python manage.py spectacular --validate` — чисто
- [ ] CI шаг проверки в `.github/workflows/ci.yml`
- [ ] Команда `python manage.py export_openapi` работает

---

## Что НЕ делать

- **НЕ открывай** Swagger UI в проде (риск утечки информации)
- **НЕ хардкодь** теги в каждом view — используй `tags=['name']` из единого списка
- **НЕ забывай** `@extend_schema` — иначе drf-spectacular будет угадывать имена сериализаторов
- **НЕ генерируй** TypeScript-типы в этой задаче (это T-3-014 ниже, после реализации эндпоинтов)

---

## Будущие шаги (упоминаются здесь, реализуются позже)

В `frontend/` (Фаза 4) добавить:

```json
// frontend/package.json
"scripts": {
  "generate:api-types": "openapi-typescript ../api-schema.yaml -o src/shared/api/types.ts"
}
```

Запускается при изменении API:
```bash
# backend
python manage.py export_openapi

# frontend
pnpm generate:api-types
```

Это договор: схема — единственный источник правды.
