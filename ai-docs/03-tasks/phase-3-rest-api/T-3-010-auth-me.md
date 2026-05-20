# T-3-010. `/api/v1/auth/*` + `/me`

> **Тип:** API
> **Приоритет:** P0
> **Оценка:** 2 часа
> **Фаза:** 3
> **Статус:** done

---

## Цель

Эндпоинты аутентификации и просмотра/редактирования собственного профиля. Без них фронт не запустится.

---

## Зависимости

- **Блокируется:** T-3-001..T-3-004
- **Блокирует:** все остальные API-задачи (тесты должны логиниться)

---

## Что нужно сделать

### Эндпоинты (по `api-contract.md`)

```
POST   /api/v1/auth/login         { username, password }       → 200 { access }, refresh в cookie
POST   /api/v1/auth/refresh       (cookie)                     → 200 { access }
POST   /api/v1/auth/logout        (cookie)                     → 204
GET    /api/v1/me                                              → 200 { id, username, email, permission, allowed_cities, telegram_id, max_chat_id }
PATCH  /api/v1/me                 { telegram_id?, max_chat_id?, email? } → 200 { ... }
POST   /api/v1/me/change-password { old_password, new_password } → 204
```

### Шаг 1. Структура

```
apps/interface/api/v1/auth/
├── __init__.py
├── urls.py
├── views.py
└── serializers.py

apps/interface/api/v1/me/
├── __init__.py
├── urls.py
├── views.py
└── serializers.py
```

### Шаг 2. Login — refresh в httpOnly cookie

`apps/interface/api/v1/auth/serializers.py`:

```python
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as DRFTokenObtainPairSerializer


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, max_length=150)
    password = serializers.CharField(required=True, max_length=128, write_only=True)


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()


class TokenObtainPairSerializer(DRFTokenObtainPairSerializer):
    """Расширяем стандартный serializer чтобы добавить кастомные claims."""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['permission'] = user.permission
        return token
```

`apps/interface/api/v1/auth/views.py`:

```python
from datetime import datetime, timedelta, timezone

from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status as http_status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from shared.throttling import LoginRateThrottle
from .serializers import LoginRequestSerializer, LoginResponseSerializer, TokenObtainPairSerializer


REFRESH_COOKIE_NAME = 'mstech_refresh'


def _refresh_cookie_kwargs():
    return {
        'key': REFRESH_COOKIE_NAME,
        'httponly': True,
        'secure': not settings.DEBUG,
        'samesite': 'Lax',
        'max_age': int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        'path': '/api/v1/auth',  # cookie доступна только на auth endpoints
    }


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]
    
    @extend_schema(
        tags=['auth'],
        summary='Вход в систему',
        request=LoginRequestSerializer,
        responses={
            200: LoginResponseSerializer,
            401: OpenApiResponse(description='Неверные учётные данные'),
        },
    )
    def post(self, request):
        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token_serializer = TokenObtainPairSerializer(data=serializer.validated_data)
        try:
            token_serializer.is_valid(raise_exception=True)
        except (InvalidToken, TokenError):
            return Response({'detail': 'Неверные учётные данные', 'code': 'invalid_credentials', 'errors': None},
                            status=http_status.HTTP_401_UNAUTHORIZED)
        
        access  = token_serializer.validated_data['access']
        refresh = token_serializer.validated_data['refresh']
        
        response = Response({'access': access})
        response.set_cookie(value=refresh, **_refresh_cookie_kwargs())
        return response


class RefreshView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['auth'],
        summary='Обновить access-токен',
        request=None,
        responses={200: LoginResponseSerializer},
    )
    def post(self, request):
        refresh_str = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not refresh_str:
            return Response({'detail': 'Refresh-токен отсутствует', 'code': 'token_missing', 'errors': None},
                            status=http_status.HTTP_401_UNAUTHORIZED)
        
        try:
            refresh = RefreshToken(refresh_str)
        except TokenError:
            return Response({'detail': 'Refresh-токен невалиден', 'code': 'token_expired', 'errors': None},
                            status=http_status.HTTP_401_UNAUTHORIZED)
        
        # ROTATE_REFRESH_TOKENS=True → выдаём новый refresh
        new_refresh = str(refresh)
        if settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS'):
            try:
                refresh.blacklist()
            except AttributeError:
                pass  # blacklist not enabled
            from rest_framework_simplejwt.tokens import RefreshToken as RT
            new_refresh = str(RT.for_user(_user_from_refresh(refresh_str)))
        
        access = str(refresh.access_token)
        response = Response({'access': access})
        response.set_cookie(value=new_refresh, **_refresh_cookie_kwargs())
        return response


class LogoutView(APIView):
    @extend_schema(
        tags=['auth'],
        summary='Выйти',
        request=None,
        responses={204: None},
    )
    def post(self, request):
        refresh_str = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if refresh_str:
            try:
                RefreshToken(refresh_str).blacklist()
            except (TokenError, AttributeError):
                pass
        
        response = Response(status=http_status.HTTP_204_NO_CONTENT)
        response.delete_cookie(REFRESH_COOKIE_NAME, path='/api/v1/auth')
        return response


def _user_from_refresh(refresh_str: str):
    """Достаёт user из refresh-токена. Используется только для ротации."""
    from rest_framework_simplejwt.tokens import UntypedToken
    from django.contrib.auth import get_user_model
    payload = UntypedToken(refresh_str).payload
    return get_user_model().objects.get(id=payload['user_id'])
```

`apps/interface/api/v1/auth/urls.py`:

```python
from django.urls import path
from .views import LoginView, RefreshView, LogoutView

urlpatterns = [
    path('login/',   LoginView.as_view(),   name='auth-login'),
    path('refresh/', RefreshView.as_view(), name='auth-refresh'),
    path('logout/',  LogoutView.as_view(),  name='auth-logout'),
]
```

### Шаг 3. `/me` endpoint

`apps/interface/api/v1/me/serializers.py`:

```python
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password


class CitySlugSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()


class MeSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    permission = serializers.CharField(read_only=True)
    allowed_cities = CitySlugSerializer(many=True, read_only=True, source='allowed_city')
    telegram_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    max_chat_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    
    def validate_new_password(self, value):
        validate_password(value)
        return value
```

`apps/interface/api/v1/me/views.py`:

```python
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import MeSerializer, ChangePasswordSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(tags=['me'], summary='Текущий пользователь', responses=MeSerializer)
    def get(self, request):
        return Response(MeSerializer(request.user).data)
    
    @extend_schema(tags=['me'], summary='Обновить профиль', request=MeSerializer, responses=MeSerializer)
    def patch(self, request):
        serializer = MeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        # MeSerializer не Django-bound, обновляем вручную:
        for field in ('email', 'telegram_id', 'max_chat_id'):
            if field in serializer.validated_data:
                setattr(request.user, field, serializer.validated_data[field])
        request.user.save(update_fields=['email', 'telegram_id', 'max_chat_id'])
        return Response(MeSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=['me'],
        summary='Сменить пароль',
        request=ChangePasswordSerializer,
        responses={
            204: OpenApiResponse(description='Пароль изменён'),
            422: OpenApiResponse(description='Старый пароль неверен или новый невалиден'),
        },
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if not request.user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'detail': 'Старый пароль неверен', 'code': 'invalid_password', 'errors': None},
                status=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        return Response(status=http_status.HTTP_204_NO_CONTENT)
```

`apps/interface/api/v1/me/urls.py`:

```python
from django.urls import path
from .views import MeView, ChangePasswordView

urlpatterns = [
    path('',                MeView.as_view(),            name='me'),
    path('change-password/', ChangePasswordView.as_view(), name='me-change-password'),
]
```

### Шаг 4. Подключить в root urls

`apps/interface/api/v1/urls.py`:

```python
from django.urls import include, path

urlpatterns = [
    path('auth/', include('apps.interface.api.v1.auth.urls')),
    path('me',    include('apps.interface.api.v1.me.urls')),  # без trailing slash → /api/v1/me
]
```

### Шаг 5. Тесты

`apps/interface/tests/test_auth.py`:

```python
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def test_login_with_valid_credentials_returns_access_and_sets_cookie(client, ms_user_factory):
    user = ms_user_factory(username='misha')
    user.set_password('correct_password')
    user.save()
    
    response = client.post('/api/v1/auth/login/', {
        'username': 'misha',
        'password': 'correct_password',
    }, format='json')
    
    assert response.status_code == 200
    assert 'access' in response.data
    assert 'mstech_refresh' in response.cookies
    assert response.cookies['mstech_refresh']['httponly']


def test_login_with_invalid_password_returns_401(client, ms_user_factory):
    user = ms_user_factory(username='misha')
    user.set_password('correct')
    user.save()
    
    response = client.post('/api/v1/auth/login/', {
        'username': 'misha',
        'password': 'wrong',
    }, format='json')
    
    assert response.status_code == 401
    assert response.data['code'] == 'invalid_credentials'


def test_refresh_returns_new_access_with_cookie(client, ms_user_factory):
    user = ms_user_factory(username='misha')
    user.set_password('p')
    user.save()
    login = client.post('/api/v1/auth/login/', {'username': 'misha', 'password': 'p'}, format='json')
    assert login.status_code == 200
    
    response = client.post('/api/v1/auth/refresh/')
    assert response.status_code == 200
    assert 'access' in response.data


def test_refresh_without_cookie_returns_401(client):
    response = client.post('/api/v1/auth/refresh/')
    assert response.status_code == 401


def test_me_returns_current_user(client, ms_user_factory):
    user = ms_user_factory(username='misha', permission='control')
    client.force_authenticate(user=user)
    
    response = client.get('/api/v1/me')
    
    assert response.status_code == 200
    assert response.data['username'] == 'misha'
    assert response.data['permission'] == 'control'
    assert 'allowed_cities' in response.data


def test_me_patch_updates_telegram_id(client, ms_user_factory):
    user = ms_user_factory()
    client.force_authenticate(user=user)
    
    response = client.patch('/api/v1/me', {'telegram_id': '12345'}, format='json')
    
    assert response.status_code == 200
    assert response.data['telegram_id'] == '12345'
    user.refresh_from_db()
    assert user.telegram_id == '12345'


def test_change_password_works(client, ms_user_factory):
    user = ms_user_factory()
    user.set_password('old_pwd')
    user.save()
    client.force_authenticate(user=user)
    
    response = client.post('/api/v1/me/change-password/', {
        'old_password': 'old_pwd',
        'new_password': 'NewSecurePassword123!',
    }, format='json')
    
    assert response.status_code == 204
    user.refresh_from_db()
    assert user.check_password('NewSecurePassword123!')


def test_change_password_with_wrong_old_returns_422(client, ms_user_factory):
    user = ms_user_factory()
    user.set_password('correct')
    user.save()
    client.force_authenticate(user=user)
    
    response = client.post('/api/v1/me/change-password/', {
        'old_password': 'wrong',
        'new_password': 'NewSecure123!',
    }, format='json')
    
    assert response.status_code == 422
    assert response.data['code'] == 'invalid_password'


def test_logout_clears_cookie(client, ms_user_factory):
    user = ms_user_factory(username='misha')
    user.set_password('p')
    user.save()
    client.post('/api/v1/auth/login/', {'username': 'misha', 'password': 'p'}, format='json')
    
    response = client.post('/api/v1/auth/logout/')
    
    assert response.status_code == 204
    # cookie cleared by setting Max-Age=0 / expired
    assert response.cookies.get('mstech_refresh', {}).value == ''
```

---

## Критерии приёмки

- [ ] `/api/v1/auth/login/`, `/refresh/`, `/logout/` работают
- [ ] Refresh-токен лежит в **httpOnly + Secure (prod) + SameSite=Lax** cookie
- [ ] Refresh-токен **только** на path `/api/v1/auth` (cookie не утекает на другие endpoints)
- [ ] Login throttle: max 10 попыток / минута / IP (`LoginRateThrottle`)
- [ ] `/api/v1/me` GET/PATCH работает
- [ ] `/api/v1/me/change-password/` работает, валидирует старый пароль
- [ ] Все тесты проходят (минимум 8 штук выше)
- [ ] OpenAPI: `/api/docs/` показывает все 6 эндпоинтов
- [ ] При отсутствии refresh cookie на `/refresh/` → 401, не 500

---

## Что НЕ делать

- **НЕ храни** access-токен в cookie — он в Authorization header (короткоживущий)
- **НЕ возвращай** refresh-токен в JSON-теле — только в httpOnly cookie
- **НЕ делай** logout без blacklist — иначе токен можно использовать после выхода
- **НЕ хардкодь** username/password в settings — только через login
- **НЕ возвращай** в `/me` permission'ы как enum-набор (это в response — string, фронт сам мапит)

---

## Безопасность

- **Brute-force защита** через `LoginRateThrottle` (10/min)
- **Refresh-token rotation** включена в `SIMPLE_JWT`
- **Blacklist** хранит revoked refresh tokens
- **Secure cookie** в prod (HTTPS only)
- **CORS** должен разрешать credentials с frontend-домена (T-3-001 настроил)
