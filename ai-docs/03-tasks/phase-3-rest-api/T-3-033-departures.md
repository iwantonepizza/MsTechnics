# T-3-033. Departures — list / detail / create / transitions

> **Тип:** API
> **Приоритет:** P1
> **Оценка:** 2 часа
> **Фаза:** 3
> **Статус:** done

---

## Цель

CRUD для выездов. Меньше задач чем у Application (нет полноценной FSM, всего 3-4 статуса), но похожая структура.

---

## Зависимости

- **Блокируется:** T-3-021, T-2-030 (DepartureStatus FK)
- **Блокирует:** дашборд / Main Menu блок «Выезды»

---

## Эндпоинты

```
GET    /api/v1/departures?status=<...>&city=<id>     → список
GET    /api/v1/departures/{id}
POST   /api/v1/departures        { description, city_id, executor_id?, time_start? } → 201
PATCH  /api/v1/departures/{id}   { executor_id?, time_start?, description? }
POST   /api/v1/departures/{id}/complete   { comment?, time_end? }
POST   /api/v1/departures/{id}/archive
DELETE /api/v1/departures/{id}                       # только status='created'
```

---

## Что нужно сделать

### Сериализаторы

`apps/interface/api/v1/departures/serializers.py`:

```python
from rest_framework import serializers

from apps.workflow.departures.models import Departure
from apps.interface.api.v1.refs.serializers import (
    CitySerializer, DepartureStatusSerializer,
)
from apps.interface.api.v1.applications.serializers import ExecutorMiniSerializer


class DepartureListItemSerializer(serializers.ModelSerializer):
    status = DepartureStatusSerializer(read_only=True)
    city = CitySerializer(read_only=True)
    executor = ExecutorMiniSerializer(read_only=True, allow_null=True)
    
    class Meta:
        model = Departure
        fields = [
            'id', 'description', 'status', 'city', 'executor',
            'time_start', 'time_end', 'last_update',
        ]


class DepartureCreateSerializer(serializers.Serializer):
    description = serializers.CharField(required=True, max_length=1000)
    city_id = serializers.IntegerField(required=True)
    executor_id = serializers.IntegerField(required=False, allow_null=True)
    time_start = serializers.DateTimeField(required=False, allow_null=True)


class DeparturePatchSerializer(serializers.Serializer):
    description = serializers.CharField(required=False, max_length=1000)
    executor_id = serializers.IntegerField(required=False, allow_null=True)
    time_start = serializers.DateTimeField(required=False, allow_null=True)


class DepartureCompleteSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    time_end = serializers.DateTimeField(required=False)
```

### ViewSet

`apps/interface/api/v1/departures/views.py`:

```python
from datetime import timedelta

from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status as http_status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, mixins

from apps.workflow.departures.models import Departure, DepartureStatus, Executor
from apps.activity.services import activity_logger
from shared.exceptions import DomainError
from shared.permissions import HasDepartmentAccess
from shared.throttling import TransitionRateThrottle
from .serializers import (
    DepartureListItemSerializer, DepartureCreateSerializer,
    DeparturePatchSerializer, DepartureCompleteSerializer,
)


class DepartureViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.CreateModelMixin,
                        mixins.UpdateModelMixin,
                        mixins.DestroyModelMixin,
                        GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DepartureListItemSerializer
    
    def get_queryset(self):
        qs = Departure.objects.select_related('status', 'city', 'executor')
        params = self.request.query_params
        
        if status_name := params.get('status'):
            qs = qs.filter(status__name=status_name)
        if city_id := params.get('city'):
            qs = qs.filter(city_id=city_id)
        
        # allowed_cities
        user = self.request.user
        if user.permission not in ('admin', 'all'):
            qs = qs.filter(city__in=user.allowed_city.all())
        
        return qs.order_by('-last_update')
    
    def get_permissions(self):
        if self.action in ('create', 'partial_update', 'complete', 'archive', 'destroy'):
            return [HasDepartmentAccess.for_('control', 'service', 'admin', 'all')()]
        return [IsAuthenticated()]
    
    @extend_schema(
        tags=['departures'],
        parameters=[
            OpenApiParameter('status', str),
            OpenApiParameter('city', int),
        ],
    )
    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)
    
    @extend_schema(tags=['departures'])
    def retrieve(self, *args, **kwargs):
        return super().retrieve(*args, **kwargs)
    
    @extend_schema(tags=['departures'], request=DepartureCreateSerializer)
    def create(self, request, *args, **kwargs):
        serializer = DepartureCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        executor = None
        if eid := serializer.validated_data.get('executor_id'):
            executor = Executor.objects.get(id=eid)
        
        departure = Departure.objects.create(
            description=serializer.validated_data['description'],
            city_id=serializer.validated_data['city_id'],
            executor=executor,
            time_start=serializer.validated_data.get('time_start'),
            status=DepartureStatus.objects.get(name='created'),
            last_update=timezone.now(),
        )
        
        activity_logger.log(
            event_type='departure.created',
            target=departure, actor=request.user,
            description=f'Создан выезд #{departure.id}',
        )
        
        return Response(
            DepartureListItemSerializer(departure).data,
            status=http_status.HTTP_201_CREATED,
        )
    
    @extend_schema(tags=['departures'], request=DeparturePatchSerializer)
    def partial_update(self, request, *args, **kwargs):
        departure = self.get_object()
        serializer = DeparturePatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        for field in ('description', 'time_start'):
            if field in serializer.validated_data:
                setattr(departure, field, serializer.validated_data[field])
        
        if 'executor_id' in serializer.validated_data:
            eid = serializer.validated_data['executor_id']
            departure.executor_id = eid if eid else None
        
        departure.last_update = timezone.now()
        departure.save()
        
        return Response(DepartureListItemSerializer(departure).data)
    
    @extend_schema(tags=['departures'], request=DepartureCompleteSerializer, summary='Завершить выезд')
    @action(detail=True, methods=['post'], throttle_classes=[TransitionRateThrottle])
    def complete(self, request, pk=None):
        departure = self.get_object()
        if departure.status.name != 'in_progress':
            raise DomainError(
                f'Завершить можно только выезд в статусе in_progress (текущий: {departure.status.name})',
                code='invalid_status_for_complete',
                http_status=409,
            )
        
        serializer = DepartureCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        departure.status = DepartureStatus.objects.get(name='completed')
        departure.time_end = serializer.validated_data.get('time_end') or timezone.now()
        departure.last_update = timezone.now()
        departure.save()
        
        activity_logger.log(
            event_type='departure.completed',
            target=departure, actor=request.user,
            description=f'Выезд #{departure.id} завершён',
            comment=serializer.validated_data.get('comment', ''),
        )
        
        return Response(DepartureListItemSerializer(departure).data)
    
    @extend_schema(tags=['departures'], request=None, summary='В архив')
    @action(detail=True, methods=['post'], throttle_classes=[TransitionRateThrottle])
    def archive(self, request, pk=None):
        departure = self.get_object()
        departure.status = DepartureStatus.objects.get(name='archived')
        departure.last_update = timezone.now()
        departure.save()
        
        activity_logger.log(
            event_type='departure.archived',
            target=departure, actor=request.user,
            description=f'Выезд #{departure.id} в архив',
        )
        
        return Response(DepartureListItemSerializer(departure).data)
    
    @extend_schema(tags=['departures'])
    def destroy(self, request, *args, **kwargs):
        departure = self.get_object()
        if departure.status.name != 'created':
            raise DomainError(
                'Удалить можно только выезд в статусе created',
                code='delete_not_allowed',
                http_status=409,
            )
        return super().destroy(request, *args, **kwargs)
```

### URLs

```python
from rest_framework.routers import DefaultRouter
from .views import DepartureViewSet

router = DefaultRouter()
router.register('departures', DepartureViewSet, basename='departures')
urlpatterns = router.urls
```

---

## Критерии приёмки

- [ ] List + retrieve + create + patch + delete + complete + archive
- [ ] Фильтры status, city, allowed_cities
- [ ] Удаление только в `created` статусе
- [ ] `complete` только из `in_progress`
- [ ] ActivityLog пишется на каждом действии
- [ ] Минимум 5 тестов: list, create, complete, archive, delete

---

## Что НЕ делать

- **НЕ строй** полноценную FSM как у Application — у выезда 4 простых статуса, проще inline
- **НЕ создавай** отдельный DepartureEvent — для выездов хватает ActivityLog
- **НЕ позволяй** менять status через PATCH — только через actions complete/archive
