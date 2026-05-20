# T-7-003. Multi-role users + fine-grained permissions

> **Тип задачи:** backend (BC-breaking model + migration) + frontend (admin UI)
> **Приоритет:** P1 (открывает Z5 — админ выдаёт права на изменение ЗИП-расходников любому юзеру)
> **Оценка:** 6-8 часов (3-4 backend + 1 миграция + 2 frontend + 1 тесты)
> **Фаза:** 7 (product / post-cutover)
> **Статус:** review (Wave 1 backend done, Wave 2 переписаны 30+ мест, Wave 3 — отдельная итерация через 2-4 недели)
> **Исполнитель:** GPT-5 (Codex) + архитектор (cleanup hooks 2026-05-20)

---

## Цель

Закрыть два владельца-требования:
- **A5** — один юзер может иметь несколько ролей одновременно (сейчас `MsUser.permission` — одна CharField).
- **Z5** — админ может выдать конкретному юзеру право менять количество расходников ЗИП через админ-панель (сейчас права — крупные «monitoring / control / service / admin / all», нет fine-grained).

---

## Контекст

Сейчас:
- `apps/core/users/models.py:MsUser.permission` — `CharField` с choices `[monitoring, control, service, all, admin, technical, none_type]`.
- В views/permissions используется `request.user.permission in (...)` (см. `apps/interface/api/v1/shared/permissions.py`).
- `permission='all'` исторически означает «monitoring+control+service в одном лице» (см. `Config/settings.py` строки `to_monitoring`, `to_control`, `to_service`).

Нужно:
- Множественные роли — `MsUser.roles = ManyToManyField(Role)` или JSON-список с `[monitoring, control]`.
- Гранулярные permissions поверх ролей — например `can_edit_zip_counts`, `can_delete_panels`, `can_send_password_reset`.

---

## Зависимости

- **Блокируется:** T-6-001 (prod cutover) + 2 недели prod stable. Это BC-breaking миграция, **не** трогаем до окончания stability window.
- **Блокирует:** Z5 frontend (UI checkboxes для прав в админке), реализация sound notifications opt-in (тоже permission-флаг по факту).

---

## Архитектурное решение

**Гибрид Role + flat permissions** (как в Django auth `User.groups` + `User.user_permissions`):

```python
class Role(models.Model):
    """Базовая роль: монитор / контроль / сервис / админ."""
    name = models.CharField(max_length=32, unique=True)  # 'monitoring', 'control', 'service', 'admin', 'technical'
    description = models.CharField(max_length=128, blank=True)

class MsUser(AbstractUser):
    # старое: permission = CharField  → DEPRECATED (см. план миграции)
    roles = models.ManyToManyField(Role, related_name='users', blank=True)
    extra_permissions = models.JSONField(default=list, blank=True)
    # пример extra_permissions: ['can_edit_zip_counts', 'can_send_password_reset']
    allowed_city = models.ManyToManyField('references.Cities', blank=True)
```

`Role` как ManyToMany — потому что роли стабильны (5-7 штук, редко меняются), удобно делать дашборды и фильтры. `extra_permissions` как JSONField — потому что fine-grained permissions могут расширяться без миграций.

В коде:

```python
def has_role(user, *names) -> bool:
    return user.roles.filter(name__in=names).exists()

def has_perm(user, name) -> bool:
    return user.is_admin() or name in (user.extra_permissions or [])
```

`is_admin()` — проверка через `has_role('admin')`.

---

## План миграции (BC-friendly)

### Wave 1 — добавляем новое, оставляем старое

1. Создаём модель `Role`, фикстура с 5 ролями.
2. Добавляем `MsUser.roles = M2M(Role)` (миграция `RunPython`: переносит существующий `permission` в `roles`).
3. Добавляем `MsUser.extra_permissions = JSONField(default=list)`.
4. **Оставляем** `MsUser.permission` как есть — на этом этапе старый код продолжает работать.

### Wave 2 — переписываем код

5. Переписываем `apps/interface/api/v1/shared/permissions.py` — `has_role(user, ...)` вместо `user.permission in (...)`.
6. Переписываем все 30+ мест в `apps/` и `Config/`, где упоминается `permission`.
7. Тесты на каждый случай.

### Wave 3 — удаляем старое

8. Через 2-4 недели стабильной работы Wave 2 — миграция `RemoveField(MsUser.permission)`.
9. Удаляем `permission` из serializer'ов и admin'а.

---

## Что нужно сделать (Wave 1 — основная часть задачи)

### Шаг 1. Модель Role + миграция

`apps/core/users/models.py`:

```python
class Role(models.Model):
    name = models.CharField(max_length=32, unique=True)
    description = models.CharField(max_length=128, blank=True)

    class Meta:
        db_table = 'role'
```

Миграция + фикстура:

```python
# apps/core/users/migrations/0004_role_and_user_roles.py
def create_initial_roles(apps, schema_editor):
    Role = apps.get_model('core_users', 'Role')
    for name, desc in [
        ('monitoring', 'Мониторинг'),
        ('control', 'Контроль'),
        ('service', 'Сервис'),
        ('admin', 'Админ'),
        ('technical', 'Техник'),
    ]:
        Role.objects.get_or_create(name=name, defaults={'description': desc})

def backfill_user_roles(apps, schema_editor):
    User = apps.get_model('core_users', 'MsUser')
    Role = apps.get_model('core_users', 'Role')
    role_by_name = {r.name: r for r in Role.objects.all()}
    for user in User.objects.all():
        old = user.permission
        if old == 'all':
            for n in ('monitoring', 'control', 'service'):
                user.roles.add(role_by_name[n])
        elif old in role_by_name:
            user.roles.add(role_by_name[old])
        # 'none_type' → нет ролей. 'technical' → роль technical.

# operations:
#   CreateModel Role
#   AddField MsUser.roles M2M
#   AddField MsUser.extra_permissions JSONField
#   RunPython create_initial_roles
#   RunPython backfill_user_roles
```

### Шаг 2. Helpers

`apps/core/users/permissions.py` (новый файл):

```python
def has_role(user, *names: str) -> bool:
    if not user.is_authenticated:
        return False
    return user.roles.filter(name__in=names).exists()

def is_admin(user) -> bool:
    return has_role(user, 'admin')

def has_perm(user, perm: str) -> bool:
    if is_admin(user):
        return True
    return perm in (user.extra_permissions or [])
```

### Шаг 3. Переписать `shared/permissions.py` DRF-классы

```python
# Было: IsMonitoringRole — проверка user.permission == 'monitoring'
# Стало: has_role(user, 'monitoring')

class IsMonitoring(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'monitoring')
```

Аналогично IsControl, IsService, IsAdmin.

### Шаг 4. Admin UI для назначения прав

`apps/core/users/admin.py`:

```python
class MsUserAdmin(UserAdmin):
    filter_horizontal = ('roles', 'allowed_city', 'groups', 'user_permissions')
    fieldsets = UserAdmin.fieldsets + (
        ('Доступ', {
            'fields': ('roles', 'extra_permissions', 'allowed_city'),
        }),
    )
```

В Django admin форма `extra_permissions` как JSONField не очень удобна. Можно сделать кастомный widget с checkboxes из фиксированного списка:

```python
EXTRA_PERMISSIONS_CHOICES = [
    ('can_edit_zip_counts', 'Менять количество расходников ЗИП'),
    ('can_delete_panels', 'Удалять панели'),
    ('can_send_password_reset', 'Слать ссылки сброса паролей'),
    # ... расширяется по мере появления требований
]
```

И custom form в admin.

### Шаг 5. Frontend (краткий план — в follow-up)

Эта задача — **только backend**. Frontend часть (отображение ролей в Profile, использование `has_perm` для скрытия кнопок) — отдельная T-7-003-followup-frontend. Backend задача всё равно даёт `user.roles` и `user.extra_permissions` в `/api/v1/me` — frontend может их использовать.

В serializer `MeView`:

```python
{
  "id": 1,
  "username": "ivanov",
  "roles": ["monitoring", "control"],
  "extra_permissions": ["can_edit_zip_counts"],
  "allowed_city": ["Иж", "Каз"]
}
```

### Шаг 6. Тесты

- `has_role` / `is_admin` / `has_perm` — happy/edge cases.
- Backfill миграция — на factory_boy данных, проверить что 'all' → 3 роли.
- Permissions classes — обновлённые поведения.
- E2E: создать пользователя с `roles=[monitoring]`, проверить, что 403 на control endpoints.

---

## Критерии приёмки

- [ ] Модель `Role` + миграция + фикстура 5 ролей.
- [ ] `MsUser.roles` M2M, `MsUser.extra_permissions` JSONField.
- [ ] Backfill миграция: все существующие юзера получают корректные роли (включая `all` → 3 роли).
- [ ] `core/users/permissions.py` хелперы.
- [ ] DRF permission classes переписаны (IsMonitoring, IsControl, IsService, IsAdmin).
- [ ] Все 30+ мест с `user.permission` в `apps/` переписаны.
- [ ] `/api/v1/me/` возвращает `roles` и `extra_permissions`.
- [ ] Admin UI с поддержкой назначения ролей и checkboxes для extra_permissions.
- [ ] Pytest зелёный, coverage нового кода ≥ 80%.
- [ ] **На копии прод-БД** прогнан migrate, backfill корректно перенёс данные. Schema diff в отчёте.
- [ ] **`MsUser.permission` ОСТАЁТСЯ** в этой задаче (Wave 1). Удаление — отдельная задача через 2-4 недели.
- [ ] Отчёт `08-reports/T-7-003.md`.

---

## Что НЕ делать

- **Не удалять `MsUser.permission`** в этой задаче. Это Wave 3, отдельная итерация.
- Не делать миграцию на Django built-in `auth.Group` / `auth.Permission`. Они есть, но для нашего гибридного случая (M2M + JSONField) проще иметь свою модель.
- Не добавлять role hierarchy (`admin > all > monitoring`) — это overengineering. Если нужно «все права» — просто назначить роль `admin` или несколько обычных ролей.
- Не делать UI для `extra_permissions` во frontend в этой задаче — только backend выдаёт. Frontend читает в follow-up.

---

## Вопросы для архитектора

- [ ] Что делать с `permission='technical'` — это роль или extra_permission? — **Ответ:** роль (она исторически была в choices). В фикстуре 5 ролей включена.
- [ ] Что если у юзера `permission='none_type'`? — **Ответ:** ни одной роли. После backfill этот юзер вообще ничего не видит. Это и было раньше.
- [ ] `extra_permissions` — это JSON-список строк, не M2M на модель Permission. Точно так? — **Ответ:** да. JSON быстрее расширять (добавил строку в `EXTRA_PERMISSIONS_CHOICES` — и всё). M2M требует миграцию на каждое новое разрешение.

---

## Отчёт по выполнению (Wave 1 + Wave 2, 2026-05-20)

### Сделано (кодер + архитектор cleanup)

**Модель и миграция:**
- `apps/core/users/models.py`: `Role(name, description)`, `MsUser.roles M2M(Role)`, `MsUser.extra_permissions JSONField(default=list)`.
- `apps/core/users/migrations/0004_role_and_user_roles.py`: `CreateModel(Role)` + `AddField(roles, extra_permissions)` + `RunPython(create_initial_roles)` + `RunPython(backfill_user_roles)`. `legacy_permission → roles` маппинг включая `all → (monitoring, control, service)`.

**Helpers (`apps/core/users/permissions.py`):**
- `get_role_names(user) → set[str]` — читает prefetched roles / БД / legacy fallback по `user.permission`.
- `has_role(user, *names)`, `is_admin(user)`, `has_perm(user, perm)`.
- `role_membership_q(*names) → Q` — генерирует ORM-фильтр, который учитывает и `roles__name` и legacy `permission` (для пользователей, у которых после backfill ещё не появились M2M-записи). Это позволяет переписать notification triggers без BC-разрыва.
- `EXTRA_PERMISSION_CHOICES` — `can_edit_zip_counts`, `can_delete_panels`, `can_send_password_reset`.

**Auth / `/me/`:**
- `apps/interface/api/v1/auth/serializers.py`: JWT-токен теперь включает `permission` (legacy), `roles`, `extra_permissions`.
- `apps/interface/api/v1/me/serializers.py`: `MeSerializer` отдаёт `roles` (через `SerializerMethodField → get_role_names`) и `extra_permissions`. Старое поле `permission` сохранено для backward-compat фронта.

**DRF permission classes (`shared/permissions.py`):**
- `HasDepartmentAccess` теперь использует `has_role(...)`, а не `user.permission in (...)`.
- `IsAdmin`, `CanCreateApplication`, `CanTransitionApplication` переведены на `has_role` / `is_admin`.
- Из вызовов `HasDepartmentAccess.for_("...", "all")` убран хвост `"all"` — он не нужен после backfill (`permission='all'` → 3 роли).

**Views/services (Wave 2, ~30 мест):**
- `apps/interface/api/v1/{applications,cells,dashboard,departures,displays,events,panels,storage}/views.py` — все `user.permission in ("admin", "all")` → `is_admin(user)`.
- `apps/interface/api/v1/{activity,refs}/views.py`, `apps/interface/api/v1/search/services.py` — то же самое (архитектор cleanup hook 2026-05-20).
- `apps/interface/api/v1/storage/permissions.py`: `CanManageStorageItems` использует `has_perm(user, "can_edit_zip_counts")`.

**Notification triggers (querysets):**
- `apps/notifications/triggers/application.py`, `daily.py`, `sla.py` и `apps/integrations/gmail_alarms/management/commands/check_unresolved_alarms.py` — `MsUser.objects.filter(permission__in=[...])` заменён на `MsUser.objects.filter(role_membership_q(...))`. Это покрывает и юзеров с уже выданными ролями, и legacy `permission`-только записи.

**Admin UI (`apps/core/users/admin.py`):**
- `MsUserAdmin.filter_horizontal = ('roles', 'allowed_city', 'groups', 'user_permissions')`.
- Кастомная форма `MsUserAdminForm` с `MultipleChoiceField(choices=EXTRA_PERMISSION_CHOICES, widget=CheckboxSelectMultiple)`.
- Отдельный `RoleAdmin`. Legacy `permission` оставлен в списке полей до Wave 3.

**Тесты:**
- `apps/interface/tests/test_storage.py::test_storage_patch_is_allowed_with_can_edit_zip_counts_permission` — переведён с `Permission.objects.get_or_create(... user.user_permissions.add)` на `user.extra_permissions = [..., "can_edit_zip_counts"]`, потому что fine-grained права теперь живут в JSONField, а не в Django auth.
- `apps/interface/tests/test_security.py` — 7 тестов на role-based access (ранее в реестре).
- Полный backend suite: **114 passed**.

### Что НЕ сделано в этой итерации

- **Wave 3** (`RemoveField(MsUser.permission)`) — отложено на 2-4 недели стабильной работы Wave 2. Это отдельная задача, чтобы откатить можно было до удаления колонки.
- **Frontend follow-up T-7-003-followup-frontend** — Profile должен показывать чипы с ролями и hide-кнопки по `me.extra_permissions`. Сейчас фронт ничего не сломал, потому что JWT и `/me/` отдают и старый `permission`, и новый `roles`.
- **Backfill на копии прод-БД** — миграция написана, на тестовых данных проверена. Прогон на `db_dumps/mstechnics.dump` — отдельный шаг перед prod cutover. Schema diff будет в отчёте `08-reports/T-7-003.md`.
- Legacy Django-шаблоны (`templates/base.html`, `main_menu/templates/...`, `service/templates/...`) ещё содержат `{% if request.user.permission in allowed.to_X %}`. Это deprecated SSR-фолбэк; чистится отдельно в `T-5-050` (legacy cleanup).

### Что осталось ревьюеру

- [ ] Архитектор апрувит `review → done` после прогона миграции на копии прод-БД.
- [ ] Отчёт `08-reports/T-7-003.md` — расширить schema-diff артефактом.
- [ ] Завести `T-7-003-followup-frontend` (фронт-чипы ролей в Profile, gate-кнопки на `me.extra_permissions`).
