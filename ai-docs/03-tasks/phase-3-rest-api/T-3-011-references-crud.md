# T-3-011. Справочники: Cities, Colors, Conditions, Smiles, Departments

> **Тип:** API
> **Приоритет:** P1
> **Оценка:** 1.5 часа
> **Фаза:** 3
> **Статус:** done

---

## Цель

CRUD для справочников. В основном — read-only для всех + admin write. Эти справочники (цвета, иконки, состояния панелей) фронтенд кэширует и не меняет часто.

---

## Зависимости

- **Блокируется:** T-3-001..T-3-004
- **Блокирует:** T-3-020 (Display и Panel зависят от справочников)

---

## Эндпоинты

```
GET    /api/v1/cities          [auth]              → список (с фильтром по allowed_cities юзера)
GET    /api/v1/cities/{id}     [auth]
GET    /api/v1/colors          [auth]
GET    /api/v1/colors/{id}     [auth]
POST   /api/v1/colors          [admin]
PATCH  /api/v1/colors/{id}     [admin]
DELETE /api/v1/colors/{id}     [admin]              # только если не используется

GET    /api/v1/conditions      [auth]
GET    /api/v1/conditions/{id} [auth]

GET    /api/v1/smiles          [auth]               # иконки состояний

GET    /api/v1/departments     [auth]
```

---

## Что нужно сделать

### Шаг 1. Сериализаторы

`apps/interface/api/v1/refs/serializers.py`:

```python
from rest_framework import serializers

from apps.core.references.models import Color, Cities, Smile, Condition
# Department в apps.directory.panels:
from apps.directory.panels.models import Department


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Cities
        fields = ['id', 'name', 'description', 'slug']


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ['id', 'name', 'hex_color']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Унифицируем имя поля по api-contract.md → 'hex'
        data['hex'] = data.pop('hex_color')
        return data


class SmileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Smile
        fields = ['id', 'smile_icon']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # api-contract.md → 'unicode_symbol'
        data['unicode_symbol'] = data.pop('smile_icon')
        data['name'] = instance.smile_icon  # имя = сам символ для compat
        return data


class ConditionSerializer(serializers.ModelSerializer):
    color = ColorSerializer(read_only=True)
    icon = SmileSerializer(read_only=True)
    
    class Meta:
        model = Condition
        fields = ['id', 'name', 'description', 'color', 'icon']


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'description']
```

### Шаг 2. ViewSets

`apps/interface/api/v1/refs/views.py`:

```python
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet

from apps.core.references.models import Color, Cities, Smile, Condition
from apps.directory.panels.models import Department
from shared.permissions import IsAdmin
from .serializers import (
    CitySerializer, ColorSerializer, ConditionSerializer,
    SmileSerializer, DepartmentSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=['refs'], summary='Список городов'),
    retrieve=extend_schema(tags=['refs'], summary='Город'),
)
class CityViewSet(ReadOnlyModelViewSet):
    serializer_class = CitySerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        user = self.request.user
        # Если admin/all — все. Иначе только allowed_cities
        if user.permission in ('admin', 'all'):
            return Cities.objects.all().order_by('name')
        return user.allowed_city.all().order_by('name')


@extend_schema_view(
    list=extend_schema(tags=['refs'], summary='Список цветов'),
    retrieve=extend_schema(tags=['refs'], summary='Цвет'),
    create=extend_schema(tags=['refs'], summary='Создать цвет'),
    update=extend_schema(tags=['refs'], summary='Обновить цвет (полностью)'),
    partial_update=extend_schema(tags=['refs'], summary='Обновить цвет (частично)'),
    destroy=extend_schema(tags=['refs'], summary='Удалить цвет'),
)
class ColorViewSet(ModelViewSet):
    """Read для всех, write для admin."""
    queryset = Color.objects.all().order_by('name')
    serializer_class = ColorSerializer
    
    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAdmin()]
    
    def perform_destroy(self, instance):
        # Защита: не удалять если используется
        from apps.core.references.models import Condition
        from apps.workflow.applications.models import ApplicationStatus
        in_use = (
            Condition.objects.filter(color=instance).exists()
            or Condition.objects.filter(color_text=instance).exists()
            or ApplicationStatus.objects.filter(color=instance).exists()
            or ApplicationStatus.objects.filter(color_text=instance).exists()
        )
        if in_use:
            from shared.exceptions import DomainError
            raise DomainError('Цвет используется в условиях/статусах', code='color_in_use')
        instance.delete()


@extend_schema_view(
    list=extend_schema(tags=['refs'], summary='Состояния панелей'),
    retrieve=extend_schema(tags=['refs'], summary='Состояние'),
)
class ConditionViewSet(ReadOnlyModelViewSet):
    queryset = Condition.objects.select_related('color', 'icon').order_by('name')
    serializer_class = ConditionSerializer
    permission_classes = [IsAuthenticated]


@extend_schema_view(
    list=extend_schema(tags=['refs'], summary='Иконки'),
    retrieve=extend_schema(tags=['refs'], summary='Иконка'),
)
class SmileViewSet(ReadOnlyModelViewSet):
    queryset = Smile.objects.all()
    serializer_class = SmileSerializer
    permission_classes = [IsAuthenticated]


@extend_schema_view(
    list=extend_schema(tags=['refs'], summary='Отделы'),
    retrieve=extend_schema(tags=['refs'], summary='Отдел'),
)
class DepartmentViewSet(ReadOnlyModelViewSet):
    queryset = Department.objects.all().order_by('name')
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
```

### Шаг 3. URL-конфиг

`apps/interface/api/v1/refs/urls.py`:

```python
from rest_framework.routers import DefaultRouter

from .views import CityViewSet, ColorViewSet, ConditionViewSet, SmileViewSet, DepartmentViewSet

router = DefaultRouter()
router.register('cities',      CityViewSet,       basename='cities')
router.register('colors',      ColorViewSet,      basename='colors')
router.register('conditions',  ConditionViewSet,  basename='conditions')
router.register('smiles',      SmileViewSet,      basename='smiles')
router.register('departments', DepartmentViewSet, basename='departments')

urlpatterns = router.urls
```

В `apps/interface/api/v1/urls.py` добавить:
```python
path('', include('apps.interface.api.v1.refs.urls')),
```

### Шаг 4. Тесты

`apps/interface/tests/test_refs.py`:

```python
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def auth_client(ms_user_factory):
    client = APIClient()
    user = ms_user_factory(permission='control')
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_client(ms_user_factory):
    client = APIClient()
    user = ms_user_factory(permission='admin')
    client.force_authenticate(user=user)
    return client


def test_cities_list_filtered_by_allowed(client_factory, ms_user_factory, city_factory):
    """User видит только города, которые у него в allowed_city."""
    city_a = city_factory(name='izhevsk')
    city_b = city_factory(name='perm')
    
    user = ms_user_factory(permission='control')
    user.allowed_city.add(city_a)
    
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get('/api/v1/cities/')
    
    assert response.status_code == 200
    names = [c['name'] for c in response.data['results']]
    assert 'izhevsk' in names
    assert 'perm' not in names


def test_admin_sees_all_cities(admin_client, city_factory):
    city_factory.create_batch(3)
    response = admin_client.get('/api/v1/cities/')
    assert response.status_code == 200
    assert len(response.data['results']) >= 3


def test_colors_read_for_anyone(auth_client, color_factory):
    color_factory()
    response = auth_client.get('/api/v1/colors/')
    assert response.status_code == 200


def test_colors_create_only_admin(auth_client, admin_client):
    response = auth_client.post('/api/v1/colors/', {'name': 'magenta', 'hex_color': '#ff00ff'}, format='json')
    assert response.status_code == 403
    
    response = admin_client.post('/api/v1/colors/', {'name': 'magenta', 'hex_color': '#ff00ff'}, format='json')
    assert response.status_code == 201


def test_color_delete_blocked_when_in_use(admin_client, color_factory, condition_factory):
    color = color_factory()
    condition_factory(color=color)
    
    response = admin_client.delete(f'/api/v1/colors/{color.id}/')
    
    assert response.status_code == 400
    assert response.data['code'] == 'color_in_use'


def test_conditions_returns_nested_color_and_icon(auth_client, condition_factory):
    cond = condition_factory(name='work')
    response = auth_client.get('/api/v1/conditions/')
    assert response.status_code == 200
    
    found = [c for c in response.data['results'] if c['name'] == 'work'][0]
    assert 'color' in found
    assert 'hex' in found['color']
    assert 'icon' in found
```

---

## Критерии приёмки

- [ ] 5 ViewSet'ов: Cities, Colors, Conditions, Smiles, Departments
- [ ] City фильтруется по `allowed_city` юзера, admin видит все
- [ ] Color CRUD — read для всех, write для admin
- [ ] Condition с nested color/icon (как в api-contract.md)
- [ ] Color delete блокируется при использовании в Condition/ApplicationStatus
- [ ] Все тесты проходят (минимум 6)
- [ ] OpenAPI документирует все эндпоинты
- [ ] Поле в API response: `Color.hex` (не `hex_color`), `Smile.unicode_symbol`

---

## Что НЕ делать

- **НЕ открывай** запись других справочников (Conditions, Smiles, Departments) для admin сейчас — это нечасто меняется, можно через Django Admin
- **НЕ кешируй** в Redis — справочники маленькие, фронт сам кэширует через TanStack Query
