# T-7-followup-display-aggregated-condition

> **Тип задачи:** backend (serializer-only, без миграций)
> **Приоритет:** P2
> **Оценка:** 30 минут
> **Фаза:** 7
> **Статус:** review
> **Исполнитель:** GPT-5 (Codex)

---

## Цель

Закрыть Q1 от дизайнера (Round 4): для DL-003 «status bullet на карточке экрана в DepartmentList» нужно знать **агрегированное** состояние экрана — наихудшее из condition его панелей. Сейчас `DisplayListSerializer` его не выводит, а frontend по списку displays не может посчитать (cells приходят только в Detail).

В модели `zip/models.py:Display` уже есть `@property current_condition`:

```python
@property
def current_condition(self):
    worst_id = self.cell_set.aggregate(worst=Max('panel__condition__id'))['worst']
    if worst_id:
        return Condition.objects.filter(id=worst_id).first()
    return None
```

Нужно вытащить это в API.

---

## Что нужно сделать

Файл: `apps/interface/api/v1/displays/serializers.py`.

```python
from apps.interface.api.v1.refs.serializers import ConditionSerializer

class DisplayListSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    aggregated_condition = serializers.SerializerMethodField()

    class Meta:
        model = Display
        fields = ["id", "name", "description", "slug", "city", "rows", "cols",
                  "aggregated_condition"]

    @extend_schema_field(ConditionSerializer(allow_null=True))
    def get_aggregated_condition(self, display):
        cond = display.current_condition
        return ConditionSerializer(cond).data if cond else None
```

**Производительность.** В `DisplayViewSet.get_queryset()` (или где он список даёт) добавить `prefetch_related("cell_set__panel__condition__color", "cell_set__panel__condition__icon")` чтобы избежать N+1 на каждый display. Проверь, что после изменения количество SQL-запросов не выросло.

---

## Критерии приёмки

- [ ] `DisplayListSerializer.aggregated_condition` отдаёт `ConditionSerializer` или `null`.
- [ ] OpenAPI schema регенерирована.
- [ ] Frontend type обновлён, поле `aggregated_condition?: Condition | null` в `shared/api/types.ts` или `schema.d.ts`.
- [ ] **SQL N+1 предотвращён** — `prefetch_related` или аналог. Замерь debug-toolbar'ом на список из 8+ displays.
- [ ] Pytest на displays — зелёный.
- [ ] Отчёт `08-reports/T-7-followup-display-aggregated-condition.md`.

---

## Что НЕ делать

- Не менять модель `Display.current_condition` — она работает, не трогаем.
- Не выводить **все** возможные агрегации (avg, count panels по condition) — только worst.
- Не добавлять в `DisplayDetailSerializer` — там уже есть полный `cells[]`, FE сам посчитает если нужно.

---

## Связанное

- T-7-100 PR-8 (`feat/department-list-merge`) — frontend будет читать поле, чтобы рисовать status bullet.
- `ai-docs/07-frontend/design-audit-2026-05-19.md` пункт DL-003.
- Q1 в `ai-docs/07-frontend/design-handoff-round-4.md`.
