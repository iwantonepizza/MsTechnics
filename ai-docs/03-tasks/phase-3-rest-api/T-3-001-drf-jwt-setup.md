# T-3-001. DRF setup + JWT аутентификация

> **Тип:** infra / setup
> **Приоритет:** P0
> **Оценка:** 2 часа
> **Фаза:** 3
> **Статус:** done

---

## Цель

Развернуть Django REST Framework + SimpleJWT, настроить middleware и базовые `urls.py` для будущих эндпоинтов. Без этого ничто из Фазы 3 не работает.

---

## Зависимости

- **Блокируется:** Фаза 2 завершена (включая T-2-fix-001)
- **Блокирует:** все T-3-XXX

---

## Что нужно сделать

### Шаг 1. Зависимости

В `pyproject.toml` (уже должно быть, проверить):
```toml
"djangorestframework>=3.15,<3.16",
"djangorestframework-simplejwt>=5.3",
"django-cors-headers>=4.3",
"drf-spectacular>=0.27",  # для T-3-002
```

После добавления — `./scripts/compile-deps.sh` (или `pip-compile`), `pip install -e ".[dev,test]"`.

### Шаг 2. Settings

Добавить в `config/settings.py`:

```python
INSTALLED_APPS += [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # ВАЖНО: первый
    *MIDDLEWARE,  # существующее
]

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',  # для admin
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'shared.pagination.CursorPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.AnonRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '2000/hour',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',  # удобно для dev
    ),
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1'],
}

# JWT
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_OBTAIN_SERIALIZER': 'apps.interface.api.v1.auth.serializers.TokenObtainPairSerializer',
}

# CORS
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CORS_ALLOW_CREDENTIALS = True  # для refresh-cookie
```

### Шаг 3. URLs скелет

`config/urls.py`:
```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # API v1
    path('api/v1/', include('apps.interface.api.v1.urls')),

    # OpenAPI schema (T-3-002 — пока заглушка)
    # path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # path('api/docs/', SpectacularSwaggerView.as_view(), name='swagger-ui'),

    # Legacy (до Фазы 4 не трогать!)
    path('', include('main_menu.urls')),
    path('user/', include('user.urls')),
    path('monitoring/', include('monitoring.urls')),
    path('control/', include('control.urls')),
    path('service/', include('service.urls')),
    path('zip/', include('zip.urls')),
    path('application/', include('application.urls')),
    path('departure/', include('departure.urls')),
    path('mail/', include('mail.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### Шаг 4. Структура `apps/interface/`

```
apps/interface/
├── __init__.py
├── apps.py             # InterfaceConfig
├── api/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       ├── urls.py            # ROOT v1 urlconf
│       ├── auth/
│       │   ├── views.py       # T-3-010
│       │   ├── serializers.py
│       │   └── urls.py
│       ├── refs/              # T-3-011, T-3-012
│       ├── displays/          # T-3-020
│       ├── panels/            # T-3-021
│       ├── cells/             # T-3-022
│       ├── storage/           # T-3-023
│       ├── applications/      # T-3-030, T-3-031, T-3-032
│       ├── departures/        # T-3-033
│       ├── activity/          # T-3-040
│       ├── events/            # T-3-041 (SSE)
│       └── health/            # T-3-050
└── tests/
```

`apps/interface/apps.py`:
```python
from django.apps import AppConfig

class InterfaceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.interface'
    label = 'interface'
    verbose_name = 'API interface'
```

В `INSTALLED_APPS` добавить `'apps.interface'`.

### Шаг 5. Скелет `apps/interface/api/v1/urls.py`

```python
"""Корневой URL conf API v1."""
from django.urls import include, path

urlpatterns = [
    path('auth/', include('apps.interface.api.v1.auth.urls')),

    # T-3-011, T-3-012 — refs:
    # path('cities/', include('apps.interface.api.v1.refs.cities.urls')),
    # ...

    # T-3-020+:
    # path('displays/', include('apps.interface.api.v1.displays.urls')),
    # ...

    # T-3-050:
    # path('health/', include('apps.interface.api.v1.health.urls')),
]
```

Каждый под-URLconf будет добавлен в своей задаче.

### Шаг 6. Auth скелет

`apps/interface/api/v1/auth/urls.py`:
```python
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

# T-3-010 наполнит view'ы
urlpatterns = [
    # path('login/', LoginView.as_view(), name='auth-login'),
    path('refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    # path('logout/', LogoutView.as_view(), name='auth-logout'),
]
```

### Шаг 7. Smoke-test

```bash
python manage.py runserver
curl http://localhost:8000/api/v1/auth/refresh/
# ожидание: 405 Method Not Allowed (т.к. POST требуется), но НЕ 500 и НЕ ImportError
```

```bash
python manage.py check
# чисто
```

---

## Критерии приёмки

- [ ] `rest_framework`, `simplejwt`, `corsheaders`, `drf_spectacular` в `INSTALLED_APPS`
- [ ] `REST_FRAMEWORK` настроен с pagination, throttling, JWT
- [ ] `SIMPLE_JWT` настроен (15 мин access, 7 дней refresh, blacklist after rotation)
- [ ] `CORS_ALLOWED_ORIGINS` из env
- [ ] `apps/interface/` создан, label='interface'
- [ ] `apps/interface/api/v1/urls.py` существует, включён в `config/urls.py` под префиксом `/api/v1/`
- [ ] `/api/v1/auth/refresh/` возвращает 405 (а не 500/404) на GET
- [ ] `python manage.py check` — чисто
- [ ] `python manage.py migrate` — применяется (создаёт таблицы blacklist)
- [ ] Legacy URLs продолжают работать (smoke: `/main_menu/`, `/zip/`)

---

## Что НЕ делать

- **НЕ переписывай** legacy `urls.py` других apps — они продолжают работать
- **НЕ добавляй** views в auth/ — это T-3-010
- **НЕ настраивай** CORS на `*` для прода — только конкретные домены через env

---

## Известные подводные камни

- **Token blacklist миграция:** SimpleJWT добавляет миграции — после `INSTALLED_APPS` обязательно `python manage.py migrate`
- **CORS_ALLOW_CREDENTIALS = True** требует, чтобы `CORS_ALLOWED_ORIGINS` был списком (не `*`)
- **`shared.pagination.CursorPagination`** ещё не существует — будет в T-3-004. Пока поставь дефолтный `'rest_framework.pagination.CursorPagination'`, в T-3-004 заменишь
