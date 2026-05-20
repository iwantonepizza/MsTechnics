# T-3-032. ApplicationEvents — read-only timeline

> **Тип:** API
> **Приоритет:** P1
> **Оценка:** 0.5 часа
> **Фаза:** 3
> **Статус:** done

---

## Цель

Endpoint для получения timeline событий заявки. Используется фронтом для модалки «История заявки» (задача владельца #3).

---

## Зависимости

- **Блокируется:** T-2-020 (ApplicationEvent), T-3-030
- **Блокирует:** Фаза 4 — фронтовый компонент `<EventTimeline>`

---

## Эндпоинт

```
GET /api/v1/applications/{id}/events
```

Ответ: список событий заявки в хронологическом порядке (по `occurred_at ASC`).

---

## Что нужно сделать

### Сериализатор

`apps/interface/api/v1/applications/serializers.py` — добавить:

```python
from apps.workflow.applications.models import ApplicationEvent


class ApplicationEventSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='actor_username')
    timestamp = serializers.DateTimeField(source='occurred_at')
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ApplicationEvent
        fields = [
            'id', 'event_type', 'user', 'timestamp', 'comment',
            'file_url', 'state_from', 'state_to', 'payload',
        ]
    
    def get_file_url(self, obj):
        return obj.file.url if obj.file else None
```

### Action в ApplicationViewSet

`apps/interface/api/v1/applications/views.py` — добавить:

```python
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action

from .serializers import ApplicationEventSerializer


@extend_schema(
    tags=['applications'],
    summary='Timeline событий заявки',
    description='Все события (created, transitions, comment_added) в хронологическом порядке.',
    responses=ApplicationEventSerializer(many=True),
)
@action(detail=True, methods=['get'])
def events(self, request, pk=None):
    app = self.get_object()
    events_qs = app.events.all().order_by('occurred_at', 'id')
    
    # без пагинации — заявка обычно имеет 5-15 событий, всё умещается
    serializer = ApplicationEventSerializer(events_qs, many=True)
    return Response({'results': serializer.data})
```

> Если ожидается > 50 событий — добавить пагинацию. Для типовой заявки (5-10 переходов + комментарии) — нет смысла.

### Тесты

```python
def test_events_returns_chronological(auth_client, application_factory):
    app = application_factory(status__name='sent_to_control')
    
    # Прогнать через несколько transitions (через service)
    from apps.workflow.applications.services import application_service
    application_service.transition(application=app, target_state='apply_in_control', user=app.user, comment='')
    
    response = auth_client.get(f'/api/v1/applications/{app.id}/events')
    
    assert response.status_code == 200
    events = response.data['results']
    assert len(events) >= 1
    # Проверить порядок ASC
    timestamps = [e['timestamp'] for e in events]
    assert timestamps == sorted(timestamps)


def test_events_excludes_other_app(auth_client, application_factory):
    app1 = application_factory()
    app2 = application_factory()
    
    response = auth_client.get(f'/api/v1/applications/{app1.id}/events')
    assert response.status_code == 200
    
    # Не должно быть событий из app2
    for ev in response.data['results']:
        assert ev.get('application_id', app1.id) == app1.id


def test_events_403_for_foreign_city(client_factory, ms_user_factory, application_factory, city_factory):
    other_city = city_factory()
    app = application_factory(display__city=other_city)
    
    user = ms_user_factory(permission='control')
    # NO add_city
    client = APIClient()
    client.force_authenticate(user=user)
    
    response = client.get(f'/api/v1/applications/{app.id}/events')
    assert response.status_code in (403, 404)
```

---

## Критерии приёмки

- [ ] `/api/v1/applications/{id}/events` работает
- [ ] Возвращает массив events отсортированных по occurred_at ASC
- [ ] Каждое событие включает: id, event_type, user, timestamp, comment, file_url, state_from, state_to, payload
- [ ] Permission через get_object — нельзя смотреть события чужого города
- [ ] Минимум 3 теста

---

## Что НЕ делать

- **НЕ позволяй** POST/PATCH/DELETE — события создаются только через FSM
- **НЕ возвращай** payload как строку — это JSONField, отдай как объект
- **НЕ делай** глобальный `/api/v1/events/` — этот endpoint **per-application**. Глобальный поток через ActivityLog (T-3-040) или SSE (T-3-041)
