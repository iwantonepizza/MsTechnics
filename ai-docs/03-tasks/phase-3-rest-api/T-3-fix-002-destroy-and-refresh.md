# T-3-fix-002. Application destroy уязвимость + Refresh rotation

> **Тип:** hotfix / security
> **Приоритет:** P1
> **Оценка:** 1 час
> **Фаза:** 3 (доработка)
> **Статус:** review

---

## Цель

Закрыть две дыры безопасности, найденные на ревью Фазы 3:

1. **B3:** `destroy()` пускает любого юзера удалить заявку, у которой `creator is None` (старые без `user_monitoring`).
2. **B4:** `RefreshView` не делает rotation (BLACKLIST_AFTER_ROTATION спецом задан, но в коде не вызывается `blacklist()`).

---

## Зависимости

- **Блокируется:** T-3-fix-001
- **Блокирует:** прод-релиз Фазы 3

---

## B3. Application destroy

### Проблема

`apps/interface/api/v1/applications/views.py:97-99`:

```python
creator = getattr(app, "user_monitoring", None)
if creator and creator != request.user.username and request.user.permission not in ("admin", "all"):
    raise DomainError("Удалять может только создатель", code="delete_window_expired")
```

Если `creator is None` (старая заявка без `user_monitoring`) — ветка с `creator and ...` пропускается → **проверка отсутствует**.

### Фикс

Инвертировать логику: «если ты не создатель — отказать», вместо «если создатель указан и не ты — отказать»:

```python
def destroy(self, request, *args, **kwargs):
    app = self.get_object()

    # 1. Только статус sent_to_control
    if app.status.name != "sent_to_control":  # после T-3-fix-001
        raise DomainError(
            "Удалять можно только заявки в статусе sent_to_control",
            code="delete_status_invalid",
        )

    # 2. Окно 5 минут с момента создания
    created = getattr(app, "time_monitoring", None) or app.last_update_date_time
    if created and timezone.now() - created > timedelta(minutes=5):
        raise DomainError("Окно для удаления истекло (5 минут)",
                           code="delete_window_expired")

    # 3. Создатель: ТОЛЬКО создатель ИЛИ admin/all
    creator = getattr(app, "user_monitoring", None)
    is_admin = request.user.permission in ("admin", "all")
    is_creator = creator and creator == request.user.username

    if not (is_creator or is_admin):
        raise DomainError(
            "Удалить может только создатель заявки",
            code="forbidden",
        )

    # 4. Audit log перед удалением
    from apps.activity.services import activity_logger
    activity_logger.log(
        actor=request.user, target=app,
        event_type="application.deleted",
        description=f"Удалена заявка #{app.id}",
        comment="Удаление в окно 5 минут",
    )

    app.delete()
    return Response(status=http_status.HTTP_204_NO_CONTENT)
```

Ключевые изменения:
- **Whitelist подход**: разрешено только если `is_creator OR is_admin` — иначе deny.
- **Если `creator is None`** — `is_creator=False`, не-admin не пройдёт.
- Добавлен `activity_logger.log()` перед `delete()` — чтобы остался след в журнале (заявка уйдёт, но лог останется).

### Тест

```python
def test_destroy_blocked_when_creator_unknown(api_client, user_with_role, application_factory):
    """Если creator не указан и юзер не admin — отказ (regression на B3)."""
    app = application_factory(
        status__name="sent_to_control",
        user_monitoring=None,  # старая заявка без поля
        time_monitoring=timezone.now(),
    )
    user = user_with_role("monitoring")
    api_client.force_authenticate(user)

    response = api_client.delete(f"/api/v1/applications/{app.id}/")

    assert response.status_code == 403  # или 409 — главное не 204
    assert app.id == app.refresh_from_db() or Application.objects.filter(id=app.id).exists()


def test_destroy_allowed_for_admin_even_if_creator_unknown(api_client, user_with_role, application_factory):
    app = application_factory(
        status__name="sent_to_control",
        user_monitoring=None,
        time_monitoring=timezone.now(),
    )
    admin = user_with_role("admin")
    api_client.force_authenticate(admin)

    response = api_client.delete(f"/api/v1/applications/{app.id}/")

    assert response.status_code == 204
    assert not Application.objects.filter(id=app.id).exists()
```

---

## B4. RefreshView без rotation

### Проблема

`apps/interface/api/v1/auth/views.py` — `RefreshView` использует стандартный `TokenRefreshView` или кастомный, но не вызывает blacklist старого refresh-токена. Settings `BLACKLIST_AFTER_ROTATION=True` без явного `.blacklist()` ничего не делает.

### Фикс

Если у вас кастомный `RefreshView`:

```python
from rest_framework_simplejwt.tokens import RefreshToken, OutstandingToken

class RefreshView(APIView):
    permission_classes = []  # AllowAny — refresh не требует auth header

    def post(self, request):
        refresh_str = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not refresh_str:
            return Response(
                {"detail": "Refresh-токен отсутствует", "code": "token_missing"},
                status=401,
            )

        try:
            old_refresh = RefreshToken(refresh_str)
        except TokenError:
            return Response({"detail": "Token invalid", "code": "token_invalid"}, status=401)

        # 1. Получить юзера из старого refresh
        from apps.core.users.models import MsUser
        user = MsUser.objects.get(id=old_refresh["user_id"])

        # 2. Блэклистить старый
        old_refresh.blacklist()

        # 3. Создать новые
        new_refresh = RefreshToken.for_user(user)
        access = str(new_refresh.access_token)

        response = Response({"access": access})
        response.set_cookie(
            key=REFRESH_COOKIE_NAME, value=str(new_refresh),
            httponly=True, secure=settings.REFRESH_COOKIE_SECURE,
            samesite="Lax", path="/api/v1/auth",
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        )
        return response
```

Если используется стандартный `rest_framework_simplejwt.views.TokenRefreshView` — он rotation делает, **но** результат отдаёт в JSON, не в cookie. Тогда либо сабкласс, либо middleware.

### Тест

```python
def test_refresh_blacklists_old_token(api_client, ms_user_factory):
    user = ms_user_factory()
    user.set_password("p"); user.save()
    api_client.post("/api/v1/auth/login/", {"username": user.username, "password": "p"}, format="json")
    
    old_refresh = api_client.cookies["mstech_refresh"].value
    
    # 1й refresh — успех
    r1 = api_client.post("/api/v1/auth/refresh/")
    assert r1.status_code == 200

    # Попытка использовать СТАРЫЙ refresh — должна провалиться (он в blacklist)
    api_client.cookies["mstech_refresh"] = old_refresh
    r2 = api_client.post("/api/v1/auth/refresh/")
    assert r2.status_code == 401
```

---

## Критерии приёмки

- [x] `destroy()` отказывает не-admin'у когда `creator is None`
- [x] `destroy()` пишет в `ActivityLog` перед удалением
- [x] `RefreshView` блэклистит старый refresh
- [x] Старый refresh после rotation покрыт regression test
- [x] Тесты добавлены (минимум 4 новых)

---

## Что НЕ делать

- **НЕ позволять** удалять заявки в любом статусе кроме `sent_to_control`
- **НЕ удалять** ActivityLog запись после удаления заявки (она остаётся)
- **НЕ ослаблять** проверку creator — старые заявки удалять может только admin
