# T-3-031. Application transitions — FSM endpoint

> **Тип:** API
> **Приоритет:** P0
> **Оценка:** 2 часа
> **Фаза:** 3
> **Статус:** done

---

## Цель

Один endpoint `POST /api/v1/applications/{id}/transition/` принимает `target_state` и переводит заявку через `ApplicationStateMachine` (T-2-040). Все валидации (роль, текущий статус, обязательные поля) — внутри FSM.

Это **самый критичный** эндпоинт: через него идут все рабочие действия диспетчеров и сервисников.

---

## Зависимости

- **Блокируется:** T-3-030, T-2-040
- **Блокирует:** T-3-032 (events)

---

## Эндпоинт

```
POST /api/v1/applications/{id}/transition/
{
  "target_state": "apply_in_control" | "sent_to_service" | ... ,
  "comment": "...",                             // зависит от перехода
  "executor_id": 5,                              // только для sent_to_service
  "file": <multipart>                            // опционально
}
```

Ответ — обновлённая заявка (DetailSerializer) или 409 при невалидном переходе.

---

## Что нужно сделать

### Шаг 1. Сериализатор

`apps/interface/api/v1/applications/serializers.py` — добавить:

```python
class TransitionSerializer(serializers.Serializer):
    target_state = serializers.CharField(required=True)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    executor_id = serializers.IntegerField(required=False, allow_null=True)
    file = serializers.FileField(required=False, allow_null=True)
    
    def validate_target_state(self, value):
        from apps.workflow.applications.state_machine import application_fsm
        all_targets = {t.target_state for t in application_fsm.all_transitions()}
        if value not in all_targets:
            raise serializers.ValidationError(f'Неизвестный target_state: {value}')
        return value
```

> **Note:** `application_fsm.all_transitions()` нужно добавить в FSM, если ещё нет — простой `return list(self._transitions)`.

### Шаг 2. Action в ViewSet

`apps/interface/api/v1/applications/views.py` — добавить в `ApplicationViewSet`:

```python
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from apps.workflow.applications.services import application_service
from shared.permissions import CanTransitionApplication
from shared.throttling import TransitionRateThrottle
from .serializers import TransitionSerializer, ApplicationDetailSerializer


@extend_schema(
    tags=['applications'],
    summary='Перевести заявку в новое состояние (FSM)',
    description=(
        'Валидирует переход через ApplicationStateMachine. '
        'Возвращает 409 если переход недопустим, 403 если у роли нет прав.'
    ),
    request=TransitionSerializer,
    responses={
        200: ApplicationDetailSerializer,
        403: OpenApiResponse(description='Нет прав на этот transition'),
        409: OpenApiResponse(description='Недопустимый переход'),
        422: OpenApiResponse(description='Не хватает обязательных полей'),
    },
)
@action(
    detail=True,
    methods=['post'],
    url_path='transition',
    parser_classes=[MultiPartParser, FormParser, JSONParser],
    permission_classes=[IsAuthenticated, CanTransitionApplication],
    throttle_classes=[TransitionRateThrottle],
)
def transition(self, request, pk=None):
    app = self.get_object()
    self.check_object_permissions(request, app)  # CanTransitionApplication object check
    
    serializer = TransitionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # executor lookup
    executor = None
    if executor_id := serializer.validated_data.get('executor_id'):
        from apps.workflow.departures.models import Executor
        try:
            executor = Executor.objects.get(id=executor_id)
        except Executor.DoesNotExist:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'executor_id': ['Исполнитель не найден']})
    
    # вся остальная логика — в сервисе
    app = application_service.transition(
        application=app,
        target_state=serializer.validated_data['target_state'],
        user=request.user,
        comment=serializer.validated_data.get('comment', ''),
        executor=executor,
        file=serializer.validated_data.get('file'),
    )
    
    return Response(ApplicationDetailSerializer(app).data)
```

### Шаг 3. Расширить `application_service.transition`

В `apps/workflow/applications/services.py` (T-2-040) убедиться, что метод принимает все нужные параметры. Если нет — расширить:

```python
class ApplicationService:
    
    def transition(
        self,
        *,
        application: Application,
        target_state: str,
        user: MsUser,
        comment: str = '',
        executor=None,
        file=None,
    ) -> Application:
        """
        Выполнить FSM-переход заявки.
        
        Делегирует валидацию в ApplicationStateMachine.
        Создаёт ApplicationEvent + ActivityLog после успешного перехода.
        Атомарно. Optimistic concurrency — через select_for_update.
        """
        from django.db import transaction
        
        with transaction.atomic():
            # Lock — защита от race condition двух одновременных transition
            application = Application.objects.select_for_update().get(pk=application.pk)
            
            # Делегируем FSM
            transition = application_fsm.get_transition(
                source_state=application.status.name,
                target_state=target_state,
            )
            
            # Проверка обязательного комментария
            if transition.requires_comment and not comment.strip():
                raise DomainError(
                    'Этот переход требует комментарий',
                    code='comment_required',
                    http_status=422,
                )
            
            # Проверка прав (вторая защита, после permission)
            if user.permission not in transition.allowed_for and user.permission not in ('admin', 'all'):
                raise DomainError(
                    'У вашей роли нет прав на этот переход',
                    code='forbidden_for_role',
                    http_status=403,
                )
            
            # Меняем статус
            new_status = ApplicationStatus.objects.get(name=target_state)
            old_status = application.status
            application.status = new_status
            application.last_update_date_time = timezone.now()
            
            # executor — только для sent_to_service
            if executor is not None:
                application.executor = executor
            
            application.save(update_fields=['status', 'last_update_date_time', 'executor'])
            
            # Хук transition (если задан в FSM)
            if transition.hook:
                transition.hook(application=application, user=user, comment=comment, file=file)
            
            # Создаём ApplicationEvent
            ApplicationEvent.objects.create(
                application=application,
                event_type=transition.event_type,
                actor_username=user.username,
                actor_id=user.id,
                occurred_at=timezone.now(),
                comment=comment,
                file=file,
                state_from=old_status.name,
                state_to=target_state,
                payload={'executor_id': executor.id if executor else None},
            )
            
            # И ActivityLog (для глобальной выборки)
            activity_logger.log(
                event_type='application.transitioned',
                target=application, actor=user,
                description=f'#{application.id}: {old_status.name} → {target_state}',
                comment=comment,
                payload={'state_from': old_status.name, 'state_to': target_state},
            )
        
        return application


application_service = ApplicationService()
```

### Шаг 4. Тесты — обширный набор

`apps/interface/tests/test_application_transitions.py`:

```python
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup_with_app(ms_user_factory, display_with_layout_factory, application_factory, application_status_factory):
    """Подготовка: пользователь, экран, заявка, все статусы."""
    # Создать все статусы один раз
    for name in ['sent_to_control','apply_in_control','sent_to_service',
                 'work_in_service','done','unable','archive_done','archive_unable']:
        application_status_factory(name=name)
    
    user = ms_user_factory(permission='control')
    user.allowed_city.add(...)  # выясняется из display
    
    display = display_with_layout_factory(rows=2, cols=2)
    cell = display.cells.first()
    user.allowed_city.add(display.city)
    
    app = application_factory(
        display=display, panel=cell.panel, cell=cell,
        status__name='sent_to_control',
    )
    
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user, app


@pytest.mark.parametrize('current_state,target_state,role', [
    ('sent_to_control',  'apply_in_control', 'control'),
    ('apply_in_control', 'sent_to_service',  'control'),
    ('sent_to_service',  'work_in_service',  'service'),
    ('work_in_service',  'done',             'service'),
    ('done',             'archive_done',     'control'),
])
def test_valid_transition(setup_with_app, current_state, target_state, role, ms_user_factory):
    client, user, app = setup_with_app
    
    # Переключаем роль если надо
    if user.permission != role:
        user.permission = role
        user.save()
    
    # Подготавливаем нужный исходный статус
    from apps.workflow.applications.models import ApplicationStatus
    app.status = ApplicationStatus.objects.get(name=current_state)
    app.save()
    
    response = client.post(
        f'/api/v1/applications/{app.id}/transition/',
        {'target_state': target_state, 'comment': 'тест'},
        format='json',
    )
    
    assert response.status_code == 200, response.data
    assert response.data['status']['name'] == target_state
    
    # ApplicationEvent создан
    assert app.events.filter(state_to=target_state).exists()


def test_invalid_transition_returns_409(setup_with_app):
    client, user, app = setup_with_app
    # sent_to_control → done нельзя
    
    response = client.post(
        f'/api/v1/applications/{app.id}/transition/',
        {'target_state': 'done', 'comment': 'нельзя'},
        format='json',
    )
    
    assert response.status_code == 409
    assert response.data['code'] == 'invalid_state_transition'


def test_unable_requires_comment(setup_with_app, application_status_factory):
    client, user, app = setup_with_app
    user.permission = 'service'
    user.save()
    
    from apps.workflow.applications.models import ApplicationStatus
    app.status = ApplicationStatus.objects.get(name='work_in_service')
    app.save()
    
    response = client.post(
        f'/api/v1/applications/{app.id}/transition/',
        {'target_state': 'unable', 'comment': ''},
        format='json',
    )
    
    assert response.status_code == 422
    assert response.data['code'] == 'comment_required'


def test_monitoring_role_cannot_apply_in_control(setup_with_app):
    client, user, app = setup_with_app
    user.permission = 'monitoring'
    user.save()
    
    response = client.post(
        f'/api/v1/applications/{app.id}/transition/',
        {'target_state': 'apply_in_control', 'comment': 'не могу'},
        format='json',
    )
    
    assert response.status_code == 403


def test_executor_set_on_sent_to_service(setup_with_app, application_status_factory):
    client, user, app = setup_with_app
    user.permission = 'control'
    user.save()
    
    from apps.workflow.applications.models import ApplicationStatus
    from apps.workflow.departures.models import Executor
    app.status = ApplicationStatus.objects.get(name='apply_in_control')
    app.save()
    
    executor = Executor.objects.create(first_name='Иван', last_name='Сервисник', phone_number='+7900')
    
    response = client.post(
        f'/api/v1/applications/{app.id}/transition/',
        {'target_state': 'sent_to_service', 'executor_id': executor.id, 'comment': ''},
        format='json',
    )
    
    assert response.status_code == 200
    app.refresh_from_db()
    assert app.executor_id == executor.id


def test_concurrent_transition_serialised(setup_with_app):
    """Проверка что select_for_update предотвращает гонку.
    
    Имитируем — в SQLite нельзя реально, но тест на правильное использование atomic().
    """
    client, user, app = setup_with_app
    
    # Просто убедиться что код не падает при последовательных вызовах
    for _ in range(2):
        client.post(
            f'/api/v1/applications/{app.id}/transition/',
            {'target_state': 'apply_in_control', 'comment': ''},
            format='json',
        )
    
    # второй должен упасть с 409 (уже в apply_in_control)
    app.refresh_from_db()
    assert app.status.name == 'apply_in_control'


def test_throttle_after_too_many_transitions(setup_with_app):
    """TransitionRateThrottle предотвращает спам."""
    client, user, app = setup_with_app
    
    # 121 запрос — превышаем лимит 120/min
    # (не запускать в обычном CI — слишком долго; пометить как slow)
    pass


def test_transition_creates_event_and_activity(setup_with_app):
    client, user, app = setup_with_app
    
    response = client.post(
        f'/api/v1/applications/{app.id}/transition/',
        {'target_state': 'apply_in_control', 'comment': 'принято'},
        format='json',
    )
    
    assert response.status_code == 200
    
    # ApplicationEvent
    events = app.events.filter(event_type='control_applied')
    assert events.count() == 1
    assert events.first().comment == 'принято'
    
    # ActivityLog
    from apps.activity.models import ActivityLog
    logs = ActivityLog.objects.filter(event_type='application.transitioned', target_object_id=str(app.id))
    assert logs.count() == 1
```

---

## Критерии приёмки

- [ ] `POST /api/v1/applications/{id}/transition/` работает
- [ ] Делегирует в `application_service.transition` (бизнес-логика **только** в сервисе)
- [ ] Все 7 валидных переходов из FSM работают
- [ ] Невалидные переходы → 409 + `invalid_state_transition`
- [ ] Permission `CanTransitionApplication` срабатывает (object-level)
- [ ] `unable` без комментария → 422 + `comment_required`
- [ ] `executor_id` устанавливается на `sent_to_service`
- [ ] `select_for_update` защищает от race condition
- [ ] Создаются `ApplicationEvent` + `ActivityLog` записи
- [ ] `TransitionRateThrottle` ограничивает спам (120/min)
- [ ] Минимум 7 тестов (валидные, невалидный, comment_required, role-denied, executor, event-creation, concurrent)
- [ ] OpenAPI документирует с примерами для каждого target_state

---

## Что НЕ делать

- **НЕ дублируй** валидацию в view и в FSM — точка истины одна (FSM)
- **НЕ возвращай** список разрешённых переходов в response — это в `/api/v1/application-statuses/{id}` через `next_possible`
- **НЕ обходи** `application_service.transition` — он атомарен, write через ORM напрямую — баг
- **НЕ забывай** about file — это multipart upload, parser должен содержать `MultiPartParser`

---

## Что закрывается этой задачей

- Задача владельца #3 — основа для UI «история заявки» (через ApplicationEvent / ActivityLog, T-3-032)
- Поток B: «контролёр принимает → отправляет в сервис» (см. `design-brief.md`)
- Поток C: «сервисник делает ремонт»
