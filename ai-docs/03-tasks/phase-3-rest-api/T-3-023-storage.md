# T-3-023. ZIP storage — Wires, Hubs, Lamels

> **Тип:** API
> **Приоритет:** P2
> **Оценка:** 1 час
> **Фаза:** 3
> **Статус:** done

---

## Цель

CRUD для расходников склада ЗИП: ламели, хабы, провода. Используется на странице ZIP-склада.

Для задачи владельца #15 (фильтрация модулей по экрану) — добавить параметр `?display=<slug>`.

---

## Зависимости

- **Блокируется:** T-3-020 (Display)

---

## Эндпоинты

```
GET   /api/v1/storage/lamels?display=<slug>
GET   /api/v1/storage/hubs?display=<slug>
GET   /api/v1/storage/wires?display=<slug>

GET   /api/v1/storage/lamels/{id}
PATCH /api/v1/storage/lamels/{id}        { count?, comment? }
DELETE /api/v1/storage/lamels/{id}       [admin/control]

# то же для hubs, wires
```

---

## Что нужно сделать

### Сериализаторы

`apps/interface/api/v1/storage/serializers.py`:

```python
from rest_framework import serializers
from apps.directory.storage.models import Wires, Hubs, Lamels


class StorageItemSerializer(serializers.ModelSerializer):
    """Один сериализатор для всех 3 типов."""
    display_id = serializers.IntegerField(read_only=True)
    
    class Meta:
        fields = ['id', 'name', 'count', 'description', 'display_id']


class WiresSerializer(StorageItemSerializer):
    class Meta(StorageItemSerializer.Meta):
        model = Wires


class HubsSerializer(StorageItemSerializer):
    class Meta(StorageItemSerializer.Meta):
        model = Hubs


class LamelsSerializer(StorageItemSerializer):
    class Meta(StorageItemSerializer.Meta):
        model = Lamels


class StoragePatchSerializer(serializers.Serializer):
    count = serializers.IntegerField(required=False, min_value=0)
    description = serializers.CharField(required=False, allow_blank=True)
```

### ViewSets — фабрика

`apps/interface/api/v1/storage/views.py`:

```python
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.directory.storage.models import Wires, Hubs, Lamels
from shared.permissions import HasDepartmentAccess
from .serializers import WiresSerializer, HubsSerializer, LamelsSerializer


def _make_storage_viewset(model, serializer, tag):
    """Фабрика — все три endpoint'а одинаковые."""
    
    class _StorageViewSet(ModelViewSet):
        queryset = model.objects.all()
        serializer_class = serializer
        permission_classes = [IsAuthenticated]
        http_method_names = ['get', 'patch', 'delete', 'head', 'options']
        
        def get_queryset(self):
            qs = model.objects.select_related('display')
            
            # Фильтр по экрану (задача владельца #15)
            params = self.request.query_params
            if display_slug := params.get('display'):
                qs = qs.filter(display__slug=display_slug)
            
            # allowed_cities
            user = self.request.user
            if user.permission not in ('admin', 'all'):
                qs = qs.filter(display__city__in=user.allowed_city.all())
            
            return qs.order_by('id')
        
        def get_permissions(self):
            if self.action in ('partial_update', 'destroy'):
                return [HasDepartmentAccess.for_('control', 'admin', 'all')()]
            return [IsAuthenticated()]
        
        @extend_schema(
            tags=[tag],
            parameters=[OpenApiParameter('display', str, description='slug экрана для фильтра')],
        )
        def list(self, *args, **kwargs):
            return super().list(*args, **kwargs)
    
    _StorageViewSet.__name__ = f'{model.__name__}ViewSet'
    return _StorageViewSet


WiresViewSet = _make_storage_viewset(Wires, WiresSerializer, 'storage')
HubsViewSet = _make_storage_viewset(Hubs, HubsSerializer, 'storage')
LamelsViewSet = _make_storage_viewset(Lamels, LamelsSerializer, 'storage')
```

### URLs

```python
from rest_framework.routers import DefaultRouter
from .views import WiresViewSet, HubsViewSet, LamelsViewSet

router = DefaultRouter()
router.register('storage/wires',  WiresViewSet,  basename='wires')
router.register('storage/hubs',   HubsViewSet,   basename='hubs')
router.register('storage/lamels', LamelsViewSet, basename='lamels')
urlpatterns = router.urls
```

---

## Критерии приёмки

- [ ] 3 ViewSet: wires, hubs, lamels
- [ ] Фильтр `?display=<slug>` работает (задача #15)
- [ ] Patch только для control/admin
- [ ] List, retrieve, patch, delete — каждый покрыт тестом

---

## Что НЕ делать

- **НЕ создавай** новые расходники через POST — это через admin (редкая операция)
- **НЕ объединяй** в один endpoint `/api/v1/storage/?type=wires` — три разные модели, лучше явный URL для каждой
