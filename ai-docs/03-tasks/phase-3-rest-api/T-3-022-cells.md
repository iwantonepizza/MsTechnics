# T-3-022. Cells endpoint + сетка экрана

> **Тип:** API
> **Приоритет:** P2
> **Оценка:** 1 час
> **Фаза:** 3
> **Статус:** done

---

## Цель

Read-only эндпоинты для ячеек. В большинстве случаев фронт получает cells через `/api/v1/displays/{slug}/` (детальный сериализатор), но отдельный endpoint нужен для:
- Быстрых обновлений конкретной ячейки через polling
- Установки/снятия панелей (через `assign-panel` action)

---

## Зависимости

- **Блокируется:** T-3-020, T-3-021

---

## Эндпоинты

```
GET   /api/v1/cells?display=<id>                    → list (фильтры)
GET   /api/v1/cells/{id}                            → detail
POST  /api/v1/cells/{id}/assign-panel { panel_id, comment? }
                                                    → ставит панель на ячейку (то же что Panel.move-to-cell)
```

---

## Что нужно сделать

### Сериализатор

`apps/interface/api/v1/cells/serializers.py`:

```python
from rest_framework import serializers

from apps.directory.displays.models import Cell
from apps.interface.api.v1.panels.serializers import PanelSerializer


class CellSerializer(serializers.ModelSerializer):
    panel = PanelSerializer(read_only=True)
    position = serializers.CharField(read_only=True)
    
    class Meta:
        model = Cell
        fields = ['id', 'position', 'row', 'col', 'panel', 'display_id']


class AssignPanelSerializer(serializers.Serializer):
    panel_id = serializers.IntegerField(required=True)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)
```

### ViewSet

`apps/interface/api/v1/cells/views.py`:

```python
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.directory.displays.models import Cell
from apps.directory.panels.services import panel_mover
from shared.throttling import TransitionRateThrottle
from .serializers import CellSerializer, AssignPanelSerializer


class CellViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CellSerializer
    
    def get_queryset(self):
        qs = Cell.objects.select_related(
            'display', 'panel__condition__color', 'panel__condition__icon',
            'panel__department',
        )
        params = self.request.query_params
        if d := params.get('display'):
            qs = qs.filter(display_id=d)
        
        # allowed_cities
        user = self.request.user
        if user.permission not in ('admin', 'all'):
            qs = qs.filter(display__city__in=user.allowed_city.all())
        
        return qs.order_by('display', 'row', 'col')
    
    @extend_schema(
        tags=['cells'],
        parameters=[OpenApiParameter('display', int)],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        tags=['cells'],
        summary='Назначить панель ячейке',
        request=AssignPanelSerializer,
        responses=CellSerializer,
    )
    @action(detail=True, methods=['post'], url_path='assign-panel', throttle_classes=[TransitionRateThrottle])
    def assign_panel(self, request, pk=None):
        cell = self.get_object()
        serializer = AssignPanelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        from apps.directory.panels.models import Panel
        panel = Panel.objects.get(id=serializer.validated_data['panel_id'])
        
        panel_mover.move_to_cell(
            panel=panel, cell=cell, user=request.user,
            comment=serializer.validated_data.get('comment', ''),
        )
        cell.refresh_from_db()
        return Response(CellSerializer(cell).data)
```

### URLs

```python
from rest_framework.routers import DefaultRouter
from .views import CellViewSet

router = DefaultRouter()
router.register('cells', CellViewSet, basename='cells')
urlpatterns = router.urls
```

---

## Критерии приёмки

- [ ] List + retrieve работают
- [ ] `assign-panel` через PanelMover
- [ ] Фильтр allowed_cities
- [ ] 4 теста: list, retrieve, assign success, assign forbidden city

---

## Что НЕ делать

- **НЕ позволяй** создавать Cell через POST — они создаются через `DisplayService.create_with_layout` (Фаза 2)
- **НЕ позволяй** удалять Cell — рушит инварианты экрана
