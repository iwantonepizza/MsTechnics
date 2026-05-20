# T-3-021. Panels — list / detail / move / replace

> **Тип:** API
> **Приоритет:** P0
> **Оценка:** 3 часа
> **Фаза:** 3
> **Статус:** done

---

## Цель

CRUD панелей + ключевые операции: смена ячейки, смена отдела, смена состояния. Через `PanelMover` сервис (T-2-041).

---

## Зависимости

- **Блокируется:** T-3-020, T-2-041 (PanelMover)
- **Блокирует:** T-3-030 (заявки используют panel)

---

## Эндпоинты

```
GET   /api/v1/panels?display=<id>&department=<id>&condition=<id>
GET   /api/v1/panels/{id}                                   → детали
PATCH /api/v1/panels/{id}                  { comment?, condition_id? }
POST  /api/v1/panels/{id}/move-to-cell     { cell_id, comment? }
POST  /api/v1/panels/{id}/remove-from-cell { comment?, condition_id? }
POST  /api/v1/panels/{id}/change-department { department, comment? }   # блокируется при активной заявке
GET   /api/v1/panels/{id}/history?kind=<...>&since=<...>
GET   /api/v1/panels/{id}/applications?status=<...>
```

---

## Что нужно сделать

### Шаг 1. Сериализаторы

`apps/interface/api/v1/panels/serializers.py`:

```python
from rest_framework import serializers

from apps.directory.panels.models import Panel
from apps.directory.displays.models import Cell

from apps.interface.api.v1.refs.serializers import ConditionSerializer


class PanelSerializer(serializers.ModelSerializer):
    """Используется и для list, и для detail."""
    condition = ConditionSerializer(read_only=True)
    application_status_name = serializers.SerializerMethodField()
    display_id = serializers.IntegerField(read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    cell_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Panel
        fields = [
            'id', 'name', 'comment', 'condition',
            'department_name', 'display_id', 'cell_id',
            'application_status_name',
        ]
    
    def get_application_status_name(self, panel):
        # из annotation если есть, иначе compute
        from apps.workflow.applications.models import Application
        return getattr(panel, 'active_application_status', None) or 'default'
    
    def get_cell_id(self, panel):
        # обратная связь cell.panel — единственная (related_name='cell')
        return panel.cell.id if hasattr(panel, 'cell') and panel.cell else None


class PanelPatchSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)
    condition_id = serializers.IntegerField(required=False)


class MoveToCellSerializer(serializers.Serializer):
    cell_id = serializers.IntegerField(required=True)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)


class RemoveFromCellSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)
    condition_id = serializers.IntegerField(required=False)


class ChangeDepartmentSerializer(serializers.Serializer):
    department = serializers.CharField(required=True)  # 'monitor' | 'service' | 'zip' | 'hand'
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)
```

### Шаг 2. ViewSet

`apps/interface/api/v1/panels/views.py`:

```python
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status as http_status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, mixins

from apps.directory.panels.models import Panel
from apps.directory.panels.services import panel_mover
from apps.activity.services import activity_logger
from shared.permissions import HasDepartmentAccess
from shared.throttling import TransitionRateThrottle
from .serializers import (
    PanelSerializer, PanelPatchSerializer,
    MoveToCellSerializer, RemoveFromCellSerializer, ChangeDepartmentSerializer,
)


class PanelViewSet(mixins.ListModelMixin,
                    mixins.RetrieveModelMixin,
                    mixins.UpdateModelMixin,
                    GenericViewSet):
    """List, retrieve, patch, плюс кастомные действия."""
    permission_classes = [IsAuthenticated]
    serializer_class = PanelSerializer
    
    def get_queryset(self):
        qs = Panel.objects.with_active_application_status() \
            .select_related('display', 'department', 'condition__color', 'condition__icon')
        
        params = self.request.query_params
        if d := params.get('display'):
            qs = qs.filter(display_id=d)
        if dept := params.get('department'):
            qs = qs.filter(department__name=dept)
        if cond := params.get('condition'):
            qs = qs.filter(condition__name=cond)
        
        # Фильтр allowed_city
        user = self.request.user
        if user.permission not in ('admin', 'all'):
            qs = qs.filter(display__city__in=user.allowed_city.all())
        
        return qs.order_by('id')
    
    @extend_schema(
        tags=['panels'],
        summary='Список панелей',
        parameters=[
            OpenApiParameter('display', int),
            OpenApiParameter('department', str),
            OpenApiParameter('condition', str),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(tags=['panels'], summary='Детали панели')
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        tags=['panels'],
        summary='Обновить панель (комментарий, состояние)',
        request=PanelPatchSerializer,
        responses=PanelSerializer,
    )
    def partial_update(self, request, *args, **kwargs):
        panel = self.get_object()
        serializer = PanelPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # comment-only — простой case
        if 'comment' in serializer.validated_data and 'condition_id' not in serializer.validated_data:
            panel.comment = serializer.validated_data['comment']
            panel.save(update_fields=['comment'])
            activity_logger.log(
                event_type='panel.comment_added',
                target=panel, actor=request.user,
                description=f'Комментарий обновлён',
                comment=panel.comment,
            )
        
        # condition change → через сервис
        if 'condition_id' in serializer.validated_data:
            from apps.core.references.models import Condition
            condition = Condition.objects.get(id=serializer.validated_data['condition_id'])
            panel_mover.change_condition(
                panel=panel,
                new_condition=condition,
                user=request.user,
                comment=serializer.validated_data.get('comment', ''),
            )
        
        panel.refresh_from_db()
        return Response(PanelSerializer(panel).data)
    
    @extend_schema(
        tags=['panels'],
        summary='Поставить панель в ячейку',
        request=MoveToCellSerializer,
        responses=PanelSerializer,
    )
    @action(
        detail=True, methods=['post'],
        url_path='move-to-cell',
        throttle_classes=[TransitionRateThrottle],
    )
    def move_to_cell(self, request, pk=None):
        panel = self.get_object()
        serializer = MoveToCellSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        from apps.directory.displays.models import Cell
        cell = Cell.objects.get(id=serializer.validated_data['cell_id'])
        
        panel_mover.move_to_cell(
            panel=panel, cell=cell,
            user=request.user,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(PanelSerializer(panel).data)
    
    @extend_schema(
        tags=['panels'],
        summary='Снять панель с ячейки',
        request=RemoveFromCellSerializer,
        responses=PanelSerializer,
    )
    @action(
        detail=True, methods=['post'],
        url_path='remove-from-cell',
        throttle_classes=[TransitionRateThrottle],
    )
    def remove_from_cell(self, request, pk=None):
        panel = self.get_object()
        serializer = RemoveFromCellSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        condition = None
        if cid := serializer.validated_data.get('condition_id'):
            from apps.core.references.models import Condition
            condition = Condition.objects.get(id=cid)
        
        panel_mover.remove_from_cell(
            panel=panel,
            user=request.user,
            new_condition=condition,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(PanelSerializer(panel).data)
    
    @extend_schema(
        tags=['panels'],
        summary='Сменить отдел панели',
        description='Блокируется если у панели есть активная заявка',
        request=ChangeDepartmentSerializer,
        responses=PanelSerializer,
    )
    @action(
        detail=True, methods=['post'],
        url_path='change-department',
        throttle_classes=[TransitionRateThrottle],
    )
    def change_department(self, request, pk=None):
        panel = self.get_object()
        serializer = ChangeDepartmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        from apps.directory.panels.models import Department
        department = Department.objects.get(name=serializer.validated_data['department'])
        
        panel_mover.change_department(
            panel=panel, new_department=department,
            user=request.user,
            comment=serializer.validated_data.get('comment', ''),
        )
        return Response(PanelSerializer(panel).data)
    
    @extend_schema(tags=['panels'], summary='История панели')
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        panel = self.get_object()
        
        from apps.activity.models import ActivityLog
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(Panel)
        qs = ActivityLog.objects.filter(target_content_type=ct, target_object_id=str(panel.id))
        
        if kind := request.query_params.get('kind'):
            qs = qs.filter(event_type__startswith=f'panel.{kind}')
        if since := request.query_params.get('since'):
            qs = qs.filter(occurred_at__gte=since)
        
        page = self.paginate_queryset(qs.order_by('-occurred_at'))
        from apps.interface.api.v1.activity.serializers import ActivityLogSerializer
        return self.get_paginated_response(ActivityLogSerializer(page, many=True).data)
    
    @extend_schema(tags=['panels'], summary='Заявки по панели')
    @action(detail=True, methods=['get'])
    def applications(self, request, pk=None):
        panel = self.get_object()
        
        from apps.workflow.applications.models import Application
        qs = Application.objects.filter(panel=panel).select_related('status', 'display', 'cell')
        
        if status := request.query_params.get('status'):
            qs = qs.filter(status__name=status)
        
        page = self.paginate_queryset(qs.order_by('-last_update_date_time'))
        from apps.interface.api.v1.applications.serializers import ApplicationListItemSerializer
        return self.get_paginated_response(ApplicationListItemSerializer(page, many=True).data)
```

### Шаг 3. URLs

```python
# apps/interface/api/v1/panels/urls.py
from rest_framework.routers import DefaultRouter
from .views import PanelViewSet

router = DefaultRouter()
router.register('panels', PanelViewSet, basename='panels')
urlpatterns = router.urls
```

### Шаг 4. Тесты

`apps/interface/tests/test_panels.py`:

```python
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(ms_user_factory, display_with_layout_factory, city_factory):
    city = city_factory(slug='izhevsk')
    user = ms_user_factory(permission='service')
    user.allowed_city.add(city)
    
    display = display_with_layout_factory(rows=3, cols=3, city=city)
    
    client = APIClient()
    client.force_authenticate(user=user)
    
    return client, user, display


def test_panels_list(setup):
    client, user, display = setup
    response = client.get(f'/api/v1/panels/?display={display.id}')
    assert response.status_code == 200
    assert len(response.data['results']) >= 9  # 3x3 cells


def test_panel_detail(setup):
    client, user, display = setup
    panel = display.cells.first().panel
    
    response = client.get(f'/api/v1/panels/{panel.id}/')
    
    assert response.status_code == 200
    assert response.data['name'] == panel.name


def test_panel_change_department_blocks_with_active_application(setup, application_factory):
    client, user, display = setup
    cell = display.cells.first()
    panel = cell.panel
    application_factory(panel=panel, cell=cell, display=display, status__name='sent_to_service')
    
    response = client.post(
        f'/api/v1/panels/{panel.id}/change-department/',
        {'department': 'zip', 'comment': 'на склад'},
        format='json',
    )
    
    assert response.status_code == 409
    assert response.data['code'] == 'panel_has_active_application'


def test_panel_change_department_succeeds_without_active_application(setup):
    client, user, display = setup
    panel = display.cells.first().panel
    
    response = client.post(
        f'/api/v1/panels/{panel.id}/change-department/',
        {'department': 'zip', 'comment': 'нет повреждений'},
        format='json',
    )
    
    assert response.status_code == 200
    panel.refresh_from_db()
    assert panel.department.name == 'zip'


def test_panel_history_returns_activity_log(setup):
    client, user, display = setup
    panel = display.cells.first().panel
    
    # действие, чтобы лог появился
    client.post(
        f'/api/v1/panels/{panel.id}/change-department/',
        {'department': 'zip'},
        format='json',
    )
    
    response = client.get(f'/api/v1/panels/{panel.id}/history/')
    assert response.status_code == 200
    assert len(response.data['results']) >= 1


def test_panel_no_access_to_foreign_city(client_factory, ms_user_factory, display_with_layout_factory, city_factory):
    other_city = city_factory(slug='kazan')
    display = display_with_layout_factory(rows=1, cols=1, city=other_city)
    panel = display.cells.first().panel
    
    user = ms_user_factory(permission='service')
    # NO add allowed_city
    client = APIClient()
    client.force_authenticate(user=user)
    
    response = client.get(f'/api/v1/panels/{panel.id}/')
    
    # либо 404 (queryset filter), либо 403 (object permission) — оба ок
    assert response.status_code in (403, 404)
```

---

## Критерии приёмки

- [ ] PanelViewSet с list, retrieve, partial_update, move-to-cell, remove-from-cell, change-department, history, applications
- [ ] Все state-изменения через `panel_mover` сервис (Фаза 2)
- [ ] `change-department` возвращает 409 при активной заявке
- [ ] Фильтры по display, department, condition, allowed_cities работают
- [ ] Annotated `application_status_name` без N+1
- [ ] Минимум 6 тестов проходят
- [ ] OpenAPI документирует все 8 эндпоинтов
- [ ] `TransitionRateThrottle` на mutation actions

---

## Что НЕ делать

- **НЕ создавай** Panel через POST `/api/v1/panels/` — панели создаются через `Display.create_with_layout` или admin
- **НЕ удаляй** Panel через DELETE — используется в FK Application; только soft-delete если потребуется (отдельная задача)
- **НЕ обходи** PanelMover — все state-изменения только через сервис, чтобы ActivityLog писался автоматически
