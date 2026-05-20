# T-3-012. ApplicationStatus + DepartureStatus справочники

> **Тип:** API
> **Приоритет:** P1
> **Оценка:** 0.5 часа
> **Фаза:** 3
> **Статус:** done

---

## Цель

Read-only эндпоинты для статусов заявок и выездов. Фронт получает с цветами/иконками, чтобы не хардкодить.

---

## Зависимости

- **Блокируется:** T-3-011 (Color/Smile сериализаторы)
- **Блокирует:** T-3-030 (заявки)

---

## Эндпоинты

```
GET /api/v1/application-statuses        → список со cleaned color, icon, allowed_transitions
GET /api/v1/application-statuses/{id}
GET /api/v1/departure-statuses          → выезды
```

---

## Что нужно сделать

### Сериализаторы

`apps/interface/api/v1/refs/serializers.py` — добавить:

```python
from apps.workflow.applications.models import ApplicationStatus
from apps.workflow.departures.models import DepartureStatus
from apps.workflow.applications.state_machine import application_fsm


class ApplicationStatusSerializer(serializers.ModelSerializer):
    color = ColorSerializer(read_only=True)
    color_text = ColorSerializer(read_only=True)
    icon = SmileSerializer(read_only=True)
    next_possible = serializers.SerializerMethodField()
    
    class Meta:
        model = ApplicationStatus
        fields = ['id', 'name', 'description', 'color', 'color_text', 'icon', 'next_possible']
    
    def get_next_possible(self, obj) -> list[dict]:
        """Список разрешённых переходов по FSM."""
        transitions = application_fsm.transitions_from(obj.name)
        return [
            {
                'target_state': t.target_state,
                'allowed_for': list(t.allowed_for),
                'requires_comment': t.requires_comment,
            }
            for t in transitions
        ]


class DepartureStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepartureStatus
        fields = ['id', 'name', 'description']
```

### ViewSets

`apps/interface/api/v1/refs/views.py` — добавить:

```python
@extend_schema_view(
    list=extend_schema(tags=['refs'], summary='Статусы заявок'),
    retrieve=extend_schema(tags=['refs'], summary='Статус'),
)
class ApplicationStatusViewSet(ReadOnlyModelViewSet):
    queryset = ApplicationStatus.objects.select_related('color', 'color_text', 'icon').order_by('id')
    serializer_class = ApplicationStatusSerializer
    permission_classes = [IsAuthenticated]


@extend_schema_view(
    list=extend_schema(tags=['refs'], summary='Статусы выездов'),
    retrieve=extend_schema(tags=['refs'], summary='Статус'),
)
class DepartureStatusViewSet(ReadOnlyModelViewSet):
    queryset = DepartureStatus.objects.all().order_by('id')
    serializer_class = DepartureStatusSerializer
    permission_classes = [IsAuthenticated]
```

### Router

В `apps/interface/api/v1/refs/urls.py` добавить:

```python
router.register('application-statuses', ApplicationStatusViewSet, basename='application-statuses')
router.register('departure-statuses',   DepartureStatusViewSet,   basename='departure-statuses')
```

### Дополнительный метод в FSM

В `apps/workflow/applications/state_machine.py` добавить метод (если ещё нет):

```python
class ApplicationStateMachine:
    # ... existing ...
    
    def transitions_from(self, state_name: str) -> list[Transition]:
        """Все разрешённые переходы из заданного состояния."""
        return [t for t in self._transitions if t.source_state == state_name]
```

---

## Критерии приёмки

- [ ] `/api/v1/application-statuses/` возвращает все статусы с color/color_text/icon nested
- [ ] Поле `next_possible` показывает массив разрешённых переходов с `target_state`, `allowed_for`, `requires_comment`
- [ ] `/api/v1/departure-statuses/` работает
- [ ] `select_related` не делает N+1 — на 8 статусов 1-2 запроса
- [ ] OpenAPI правильно документирует
- [ ] Минимум 4 теста: list, retrieve, next_possible содержит правильные переходы, departure-statuses

---

## Что НЕ делать

- **НЕ возвращай** все ApplicationStatus в ApplicationSerializer (их 8) — только id+name+nested
- **НЕ дублируй** логику FSM в сериализаторе — всегда через `application_fsm`
