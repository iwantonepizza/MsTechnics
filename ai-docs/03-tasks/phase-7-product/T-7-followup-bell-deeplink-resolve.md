# T-7-followup-bell-deeplink-resolve

> **Тип задачи:** backend (optional / nice-to-have)
> **Приоритет:** P3
> **Оценка:** 1-1.5 часа
> **Фаза:** 7
> **Статус:** review (но не блокирует T-7-100)
> **Исполнитель:** GPT-5 (Codex)

---

## Цель

Дизайнер в Round 4 указал на проблему deep-link'ов в `<NotificationBell>` popover: для notification с `target_kind="application"` сейчас формируется ссылка `/applications/{id}` (через `buildDeepLink()` в `NotificationBell.tsx`), но **такого маршрута нет в SPA** — карточка заявки живёт внутри `DisplayViewPage` как detail-pane.

PR-6 из T-7-100 даёт **временный fallback** на `/control?app_id={id}` — это работает, но не учитывает фактический city экрана. То есть юзер открывает уведомление о заявке в Казани и попадает в /control с фильтром, но не на конкретный экран.

Идеальное решение — backend endpoint, который для notification возвращает готовый deep-link с учётом city/display.

---

## Что нужно сделать

### Вариант A — endpoint `/applications/{id}/resolve-link/`

```python
# apps/interface/api/v1/applications/views.py
@action(detail=True, methods=["get"], url_path="resolve-link")
def resolve_link(self, request, *_args, **_kwargs):
    app = self.get_object()
    return Response({
        "department": "control",  # или вычислить по статусу/исполнителю
        "city_slug": app.display.city.slug,
        "display_slug": app.display.slug,
        "app_id": app.id,
    })
```

Frontend `NotificationBell.tsx` для `target_kind="application"` дёргает этот endpoint и редиректит.

### Вариант B — расширить `NotificationInboxItemSerializer`

В `apps/interface/api/v1/notifications/serializers.py` добавить computed-поле `deep_link_path` напрямую — `/{dept}/{city.slug}/{display.slug}?app_id={id}`. Frontend читает готовое поле.

**Архитектор рекомендует Вариант B** — меньше HTTP-запросов, проще FE-логика. Серверу всё равно нужен JOIN на target_application → display → city для рендера уведомления, можно вернуть готовую ссылку.

---

## Критерии приёмки

- [ ] `NotificationInboxItemSerializer.deep_link_path` (или `/applications/{id}/resolve-link/`) возвращает корректный путь для application/departure/panel targets.
- [ ] Pytest на `/notifications/inbox/` зелёный.
- [ ] OpenAPI schema регенерирована.
- [ ] Frontend `NotificationBell.buildDeepLink()` использует `deep_link_path` если он есть, fallback на старую логику если null.
- [ ] Отчёт `08-reports/T-7-followup-bell-deeplink-resolve.md`.

---

## Что НЕ делать

- Не делать оба варианта параллельно — выбрать один (рекомендация B).
- Не покрывать **все** target_kind сразу — `application`, `departure`, `panel` достаточно. Остальное возвращай null.
- Не блокировать T-7-100 — Round 4 интеграция и без этого даёт **рабочий** fallback на `/control?app_id=`.

---

## Связанное

- T-7-100 PR-6 (`fix/header-icon-buttons`) — текущий fallback.
- T-7-followup-applications-display-city — на serializer-уровне даст `city.slug`, после этого deep-link можно строить и в frontend без endpoint'а. **Эта задача (bell-deeplink-resolve) теряет смысл, если applications-display-city сделана.** Решить после её закрытия.
