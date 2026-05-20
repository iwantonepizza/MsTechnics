# T-7-followup-applications-display-city

> **Тип задачи:** backend (serializer-only, без миграций)
> **Приоритет:** P1 (блокирует PR-10 из T-7-100)
> **Оценка:** 20 минут (фактически ~30-40 мин с тестом и schema regen)
> **Фаза:** 7
> **Статус:** review (отчёт `08-reports/T-7-followup-applications-display-city.md`, PR-10 разблокирован и закрыт)
> **Исполнитель:** GPT-5 (Codex)

---

## Цель

Закрыть Q3 от дизайнера (Round 4): `/dashboard/` и любые ответы с `ApplicationListItemSerializer` сейчас **не отдают** `app.display.city.slug`. Это блокирует PR-10 `feat/dashboard-app-link` из T-7-100 — frontend не может построить deep-link `/{department}/{citySlug}/{displaySlug}?app_id=...` без city.

---

## Что нужно сделать

Файл: `apps/interface/api/v1/applications/serializers.py`.

Текущий `DisplayMiniSerializer`:

```python
class DisplayMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    slug = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_null=True)
```

Расширить:

```python
class DisplayMiniCitySerializer(serializers.Serializer):
    """Минимальный city-DTO внутри Display для deep-link'ов."""
    slug = serializers.CharField(allow_null=True)
    name = serializers.CharField()


class DisplayMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    slug = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_null=True)
    city = DisplayMiniCitySerializer(read_only=True)
```

Это один JOIN, дешёво — `display.city` уже select_related во всех places, где грузятся applications.

---

## Критерии приёмки

- [ ] `DisplayMiniSerializer.city` отдаёт `{slug, name}`.
- [ ] OpenAPI schema регенерирована (`make api-schema && make fe-types`).
- [ ] Frontend type `DisplayMini` в `shared/api/types.ts` или сгенерированной `schema.d.ts` имеет поле `city`.
- [ ] `GET /api/v1/dashboard/` ответ включает `monitoring.recent[].display.city.slug`.
- [ ] Существующие pytest на applications/dashboard — зелёные.
- [ ] Отчёт `08-reports/T-7-followup-applications-display-city.md`.

---

## Что НЕ делать

- Не менять модель `Display` или БД. Это чистый serializer-патч.
- Не трогать `ApplicationDetailSerializer` или другие сериализаторы вне списка. Если в будущем понадобится city в detail — отдельной задачей.
- Не менять FE deep-link логику здесь — это PR-10 из T-7-100.

---

## Связанное

- T-7-100 PR-10 (`feat/dashboard-app-link`).
- `ai-docs/07-frontend/design-audit-2026-05-19.md` пункт M-001.
- Q3 в `ai-docs/07-frontend/design-handoff-round-4.md`.
