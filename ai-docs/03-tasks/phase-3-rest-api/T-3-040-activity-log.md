# T-3-040. ActivityLog read endpoint + фильтры

> **Тип:** API
> **Приоритет:** P1
> **Оценка:** 1 час
> **Фаза:** 3
> **Статус:** done

---

## Цель

Глобальный read-only endpoint для журнала активности. Используется фронтом в виджете «Журнал событий по экрану/панели/заявке» (задача владельца #11).

---

## Зависимости

- **Блокируется:** T-2-022 (ActivityLog)
- **Блокирует:** T-3-041 (SSE использует тот же сериализатор)

---

## Эндпоинт

```
GET /api/v1/activity-log
    ?display=<slug>              # фильтр по экрану (через target=Display или panel.display=...)
    &kind=<event_type prefix>    # 'panel.', 'application.', 'display.'
    &since=<ISO datetime>
    &before=<ISO datetime>
    &actor=<username>
```

---

## Что нужно сделать

### Сериализатор

`apps/interface/api/v1/activity/serializers.py`:

```python
from rest_framework import serializers

from apps.activity.models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    target_kind = serializers.SerializerMethodField()
    target_display = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ActivityLog
        fields = [
            'id', 'event_type',
            'target_kind', 'target_object_id', 'target_display',
            'actor_username', 'actor_id',
            'occurred_at', 'description', 'comment',
            'file_url', 'payload',
        ]
    
    def get_target_kind(self, obj):
        ct = obj.target_content_type
        return ct.model if ct else None
    
    def get_target_display(self, obj):
        """Кратко описать на что указывает событие. Зависит от типа target."""
        target = obj.target
        if target is None:
            return None
        # Display
        if hasattr(target, 'description'):  # Display
            return {'kind': 'display', 'description': target.description, 'slug': getattr(target, 'slug', None)}
        # Panel — name
        if hasattr(target, 'name'):
            return {'kind': 'panel', 'name': target.name}
        # Application — id
        return {'kind': obj.target_content_type.model, 'id': obj.target_object_id}
    
    def get_file_url(self, obj):
        return obj.file.url if obj.file else None
```

### View

`apps/interface/api/v1/activity/views.py`:

```python
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.activity.models import ActivityLog
from .serializers import ActivityLogSerializer


class ActivityLogViewSet(ReadOnlyModelViewSet):
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = ActivityLog.objects.select_related('target_content_type').order_by('-occurred_at', '-id')
        params = self.request.query_params
        
        if kind := params.get('kind'):
            qs = qs.filter(event_type__startswith=kind)
        if since := params.get('since'):
            qs = qs.filter(occurred_at__gte=since)
        if before := params.get('before'):
            qs = qs.filter(occurred_at__lt=before)
        if actor := params.get('actor'):
            qs = qs.filter(actor_username=actor)
        
        # Фильтр по display — собирает события Display + Panel.display + Application.display
        if display_slug := params.get('display'):
            from django.contrib.contenttypes.models import ContentType
            from apps.directory.displays.models import Display
            from apps.directory.panels.models import Panel
            from apps.workflow.applications.models import Application
            
            display = Display.objects.filter(slug=display_slug).first()
            if not display:
                return qs.none()
            
            ct_display = ContentType.objects.get_for_model(Display)
            ct_panel = ContentType.objects.get_for_model(Panel)
            ct_application = ContentType.objects.get_for_model(Application)
            
            panel_ids = list(Panel.objects.filter(display=display).values_list('id', flat=True))
            app_ids = list(Application.objects.filter(display=display).values_list('id', flat=True))
            
            from django.db.models import Q
            qs = qs.filter(
                Q(target_content_type=ct_display, target_object_id=str(display.id)) |
                Q(target_content_type=ct_panel, target_object_id__in=[str(i) for i in panel_ids]) |
                Q(target_content_type=ct_application, target_object_id__in=[str(i) for i in app_ids])
            )
        
        # allowed_cities — пропускаем только лог по городам, к которым доступ
        # (для упрощения: если есть display filter — он уже в allowed_cities у юзера. Без display — admin only.)
        user = self.request.user
        if user.permission not in ('admin', 'all') and not params.get('display'):
            # Без display-фильтра нет надёжного способа фильтровать по городу через GenericFK
            # → ограничиваем admin'ами. Для не-admin'ов — обязательный display-параметр.
            qs = qs.none()
        
        return qs
    
    @extend_schema(
        tags=['activity'],
        summary='Журнал активности',
        parameters=[
            OpenApiParameter('display', str, description='slug экрана (обязательно для не-admin)'),
            OpenApiParameter('kind', str, description='префикс event_type: panel., application., display.'),
            OpenApiParameter('since', str),
            OpenApiParameter('before', str),
            OpenApiParameter('actor', str),
        ],
    )
    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)
    
    @extend_schema(tags=['activity'])
    def retrieve(self, *args, **kwargs):
        return super().retrieve(*args, **kwargs)
```

### URLs

```python
from rest_framework.routers import DefaultRouter
from .views import ActivityLogViewSet

router = DefaultRouter()
router.register('activity-log', ActivityLogViewSet, basename='activity-log')
urlpatterns = router.urls
```

---

## Критерии приёмки

- [ ] List + retrieve работают
- [ ] Фильтры: display, kind, since, before, actor
- [ ] Display-фильтр включает события Display + Panel.display + Application.display
- [ ] Не-admin без display-фильтра → пустой результат (защита)
- [ ] Сериализатор показывает `target_kind`, `target_display`
- [ ] Минимум 5 тестов

---

## Что НЕ делать

- **НЕ позволяй** create/update/delete — журнал immutable, пишется только через `activity_logger`
- **НЕ возвращай** raw GenericFK — всегда через `target_kind` и `target_display`
- **НЕ забудь** select_related('target_content_type'), иначе N+1 на сериализации

---

## Что закрывается этой задачей

- Задача владельца #11 — единый журнал событий по экрану/панели
