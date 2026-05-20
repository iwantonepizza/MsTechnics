# T-3-030. Applications — list / detail / create / delete + filters

> **Тип:** API
> **Приоритет:** P0
> **Оценка:** 2.5 часа
> **Фаза:** 3
> **Статус:** done

---

## Цель

CRUD заявок без transitions (transitions в T-3-031). Включая фильтрацию по box (Запросы/В работе/Архив/...) и сортировку по вкладкам.

---

## Зависимости

- **Блокируется:** T-3-021 (Panel)
- **Блокирует:** T-3-031 (transitions), T-3-032 (events)

---

## Эндпоинты

```
GET    /api/v1/applications?display=<slug>&box=<n>&cell=<pos>&panel=<id>&ordering=...
GET    /api/v1/applications/{id}
POST   /api/v1/applications      { panel_id, cell_id, display_id, comment, file? }
DELETE /api/v1/applications/{id}                      # только sent_to_control от создателя в окне 5 минут
```

---

## Что нужно сделать

### Сериализаторы

`apps/interface/api/v1/applications/serializers.py`:

```python
from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta

from apps.workflow.applications.models import Application, ApplicationStatus
from apps.interface.api.v1.refs.serializers import ApplicationStatusSerializer, CitySerializer


class CellMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    position = serializers.CharField()


class DisplayMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    slug = serializers.CharField()
    description = serializers.CharField()
    city = CitySerializer(read_only=True)


class PanelMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class ExecutorMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


class ApplicationListItemSerializer(serializers.ModelSerializer):
    """Краткая версия для списков."""
    status = ApplicationStatusSerializer(read_only=True)
    display = DisplayMiniSerializer(read_only=True)
    panel = PanelMiniSerializer(read_only=True)
    cell = CellMiniSerializer(read_only=True)
    
    class Meta:
        model = Application
        fields = [
            'id', 'status', 'display', 'panel', 'cell',
            'last_update_date_time',
        ]


class ApplicationDetailSerializer(serializers.ModelSerializer):
    """Полная информация. Включает comment + последние events."""
    status = ApplicationStatusSerializer(read_only=True)
    display = DisplayMiniSerializer(read_only=True)
    panel = PanelMiniSerializer(read_only=True)
    cell = CellMiniSerializer(read_only=True)
    executor = ExecutorMiniSerializer(read_only=True, allow_null=True)
    initial_comment = serializers.SerializerMethodField()
    
    class Meta:
        model = Application
        fields = [
            'id', 'status', 'display', 'panel', 'cell', 'executor',
            'initial_comment', 'last_update_date_time', 'created_at',
        ]
    
    def get_initial_comment(self, obj) -> str:
        # До T-2-021 — берём из comment_monitoring; после — из events.first
        ev = obj.events.filter(event_type='created').first()
        if ev:
            return ev.comment
        return getattr(obj, 'comment_monitoring', '') or ''
    
    @property
    def created_at(self):
        return getattr(self.instance, 'time_monitoring', None)


class ApplicationCreateSerializer(serializers.Serializer):
    display_id = serializers.IntegerField(required=True)
    panel_id = serializers.IntegerField(required=True)
    cell_id = serializers.IntegerField(required=True)
    comment = serializers.CharField(required=True, max_length=2000)
    file = serializers.FileField(required=False, allow_null=True)
```

### Маппинг box → filter

```python
# apps/interface/api/v1/applications/filters.py

BOX_TO_STATUSES = {
    'received':            ['sent_to_control'],
    'at_work':             ['apply_in_control', 'sent_to_service', 'work_in_service'],
    'complete':            ['done', 'unable'],
    'archive':             ['archive_done', 'archive_unable'],
    'application_history': [],  # только закрытые: archive_*, done, unable
    'all':                 None,  # всё
    'unable':              ['unable', 'archive_unable'],
}


def apply_box_filter(qs, box: str):
    """Применить фильтр по box-параметру."""
    if box == 'application_history':
        return qs.filter(status__name__in=['done', 'unable', 'archive_done', 'archive_unable'])
    if box == 'all':
        return qs
    statuses = BOX_TO_STATUSES.get(box)
    if statuses is None:  # unknown box — пусто
        return qs.none()
    return qs.filter(status__name__in=statuses)
```

### ViewSet

`apps/interface/api/v1/applications/views.py`:

```python
from datetime import timedelta

from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, mixins

from apps.workflow.applications.models import Application
from apps.workflow.applications.services import application_service
from shared.exceptions import DomainError
from shared.permissions import CanCreateApplication
from shared.throttling import TransitionRateThrottle
from .filters import apply_box_filter
from .serializers import (
    ApplicationListItemSerializer, ApplicationDetailSerializer,
    ApplicationCreateSerializer,
)


class DeleteApplicationNotAllowed(DomainError):
    """Удаление возможно только в статусе sent_to_control в течение 5 минут после создания."""
    code = 'delete_window_expired'
    http_status = http_status.HTTP_409_CONFLICT


class ApplicationViewSet(mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.CreateModelMixin,
                          mixins.DestroyModelMixin,
                          GenericViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = Application.objects.select_related(
            'status', 'status__color', 'status__color_text', 'status__icon',
            'display', 'display__city', 'panel', 'cell', 'executor',
        )
        params = self.request.query_params
        
        if display_slug := params.get('display'):
            qs = qs.filter(display__slug=display_slug)
        if cell := params.get('cell'):
            qs = qs.filter(cell__id=cell)  # либо по position — в зависимости от UX
        if panel_id := params.get('panel'):
            qs = qs.filter(panel_id=panel_id)
        
        if box := params.get('box', 'received'):
            qs = apply_box_filter(qs, box)
        
        # allowed_cities
        user = self.request.user
        if user.permission not in ('admin', 'all'):
            qs = qs.filter(display__city__in=user.allowed_city.all())
        
        # Сортировка из query (?ordering=-id, -last_update_date_time)
        ordering = params.get('ordering', '-last_update_date_time,-id')
        qs = qs.order_by(*ordering.split(','))
        
        return qs
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ApplicationDetailSerializer
        if self.action == 'create':
            return ApplicationCreateSerializer
        return ApplicationListItemSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), CanCreateApplication()]
        return [IsAuthenticated()]
    
    @extend_schema(
        tags=['applications'],
        summary='Список заявок',
        parameters=[
            OpenApiParameter('display', str, description='slug экрана'),
            OpenApiParameter('box', str, description='received|at_work|complete|archive|application_history|all|unable'),
            OpenApiParameter('cell', int, description='ID ячейки'),
            OpenApiParameter('panel', int, description='ID панели'),
            OpenApiParameter('ordering', str, description='Поля сортировки через запятую'),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(tags=['applications'], summary='Детали заявки')
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(tags=['applications'], summary='Создать заявку', request=ApplicationCreateSerializer)
    def create(self, request, *args, **kwargs):
        serializer = ApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        app = application_service.create(
            display_id=serializer.validated_data['display_id'],
            panel_id=serializer.validated_data['panel_id'],
            cell_id=serializer.validated_data['cell_id'],
            comment=serializer.validated_data['comment'],
            file=serializer.validated_data.get('file'),
            user=request.user,
        )
        return Response(
            ApplicationDetailSerializer(app).data,
            status=http_status.HTTP_201_CREATED,
        )
    
    @extend_schema(tags=['applications'], summary='Удалить заявку (только sent_to_control в окне 5 минут)')
    def destroy(self, request, *args, **kwargs):
        app = self.get_object()
        
        if app.status.name != 'sent_to_control':
            raise DeleteApplicationNotAllowed('Удалять можно только заявки в статусе sent_to_control')
        
        # Проверка владельца — only the creator
        creator_username = getattr(app, 'user_monitoring', None)
        if creator_username and creator_username != request.user.username:
            raise DeleteApplicationNotAllowed('Удалять может только создатель заявки')
        
        # Проверка окна
        created_at = getattr(app, 'time_monitoring', None) or app.last_update_date_time
        if created_at and timezone.now() - created_at > timedelta(minutes=5):
            raise DeleteApplicationNotAllowed()
        
        app.delete()
        return Response(status=http_status.HTTP_204_NO_CONTENT)
```

### URLs

```python
from rest_framework.routers import DefaultRouter
from .views import ApplicationViewSet

router = DefaultRouter()
router.register('applications', ApplicationViewSet, basename='applications')
urlpatterns = router.urls
```

### Тесты (минимум)

```python
def test_applications_list(auth_client, application_factory):
    application_factory.create_batch(5, status__name='sent_to_control')
    response = auth_client.get('/api/v1/applications/?box=received')
    assert response.status_code == 200
    assert len(response.data['results']) == 5

def test_applications_filtered_by_box_at_work(auth_client, application_factory):
    application_factory(status__name='sent_to_control')  # received
    application_factory(status__name='work_in_service')   # at_work
    application_factory(status__name='archive_done')      # archive
    
    response = auth_client.get('/api/v1/applications/?box=at_work')
    assert len(response.data['results']) == 1
    assert response.data['results'][0]['status']['name'] == 'work_in_service'

def test_archive_box_excludes_active(auth_client, application_factory):
    application_factory(status__name='sent_to_control')
    application_factory(status__name='archive_done')
    
    response = auth_client.get('/api/v1/applications/?box=archive')
    statuses = [r['status']['name'] for r in response.data['results']]
    assert 'archive_done' in statuses
    assert 'sent_to_control' not in statuses

def test_create_application(auth_client, display_with_layout_factory, ms_user_factory):
    user = ms_user_factory(permission='monitoring')
    cell = display_with_layout_factory(rows=2, cols=2).cells.first()
    
    auth_client.force_authenticate(user=user)
    response = auth_client.post('/api/v1/applications/', {
        'display_id': cell.display_id,
        'panel_id': cell.panel_id,
        'cell_id': cell.id,
        'comment': 'Моргает',
    }, format='json')
    
    assert response.status_code == 201
    assert response.data['status']['name'] == 'sent_to_control'

def test_delete_within_window(auth_client, application_factory, ms_user_factory):
    user = ms_user_factory(username='creator', permission='monitoring')
    auth_client.force_authenticate(user=user)
    app = application_factory(status__name='sent_to_control', user_monitoring='creator')
    
    response = auth_client.delete(f'/api/v1/applications/{app.id}/')
    assert response.status_code == 204

def test_delete_blocked_after_window(auth_client, application_factory, ms_user_factory):
    from datetime import timedelta
    from django.utils import timezone
    
    user = ms_user_factory(username='creator', permission='monitoring')
    auth_client.force_authenticate(user=user)
    
    app = application_factory(
        status__name='sent_to_control',
        user_monitoring='creator',
        time_monitoring=timezone.now() - timedelta(minutes=10),
    )
    
    response = auth_client.delete(f'/api/v1/applications/{app.id}/')
    assert response.status_code == 409
    assert response.data['code'] == 'delete_window_expired'
```

---

## Критерии приёмки

- [ ] List с фильтрами: display, cell, panel, box, ordering
- [ ] 7 значений `box` правильно мапятся на статусы
- [ ] Detail с ApplicationStatusSerializer + display/panel/cell/executor mini
- [ ] Create через `application_service.create(...)`
- [ ] Delete блокируется вне окна / для других пользователей / для не-sent_to_control
- [ ] Archive не появляется в `?box=received` (задача владельца #7)
- [ ] OpenAPI документирует все эндпоинты
- [ ] Минимум 6 тестов проходят

---

## Что НЕ делать

- **НЕ ставь** transitions в этой задаче — это T-3-031
- **НЕ возвращай** все 28 денормализованных полей в response — пользоваться `events` (T-3-032)
- **НЕ позволяй** менять status через PATCH — только через `/transition/` action
