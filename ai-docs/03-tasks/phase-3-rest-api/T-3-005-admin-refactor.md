# T-3-005. Перенести admin'ки в `apps/`

> **Тип:** refactor / cleanup
> **Приоритет:** P1
> **Оценка:** 1.5 часа
> **Фаза:** 3
> **Статус:** done

---

## Цель

После Фазы 2 модели переехали в `apps/`, но admin-классы остались в legacy-папках (`zip/admin.py`, `application/admin.py` и т.д.). Это работает (через compat-shim re-exports), **но**:

1. При удалении `Application.comment_monitoring` и других 28 полей в T-2-021 (отложено) `application/admin.py` упадёт — там `fields=[..., 'comment_monitoring', ...]` хардкодом.
2. Админка `Contact` сейчас в `departure/admin.py:38` — после T-2-fix-001 правильнее перенести в `apps/workflow/departures/admin.py`.
3. Это технический долг — Фаза 4 (когда мы удаляем legacy templates) не сможет дропнуть legacy-папки, пока в них admin.

Перенос **закрывает баг B2 из ревью архитектора Фазы 2**.

---

## Зависимости

- **Блокируется:** T-2-fix-001 (Contact на месте)
- **Блокирует:** T-2-021 (drop denormalized fields — хочет, чтобы admin был обновлён)

---

## Что нужно сделать

### Шаг 1. Создать `admin.py` в каждом sub-app `apps/`

| Источник (legacy) | Целевой файл |
|---|---|
| `main/admin.py` | `apps/core/references/admin.py` |
| `user/admin.py` | `apps/core/users/admin.py` |
| `zip/admin.py` (Display, Cell, Wires, Hubs, Lamels, PhotoDisplay) | разнести по: `apps/directory/displays/admin.py`, `apps/directory/storage/admin.py` |
| `zip/admin.py` (Panels, Department) | `apps/directory/panels/admin.py` |
| `zip/admin.py` (DailyTask) | `apps/workflow/daily_tasks/admin.py` (после T-2-fix-002) |
| `application/admin.py` | `apps/workflow/applications/admin.py` |
| `departure/admin.py` (включая Contact) | `apps/workflow/departures/admin.py` |
| `main_menu/admin.py` | TBD — что там есть, перенести соответственно |
| `mail/admin.py` | пока **не переносим** — это интеграция Фазы 5 |

### Шаг 2. Качество переноса

**Не копируй слепо!** При переносе:

- Замени `from <legacy>.models import *` на явные импорты из новых мест
- Оставь те же `list_display`, `search_fields`, `list_filter`, `fields`
- **Если в `fields=[...]` есть удалённые/устаревшие поля** — пометь для T-2-021 удаления (но не удаляй сейчас)
- Декоратор `@admin.register(...)` — предпочтительнее, чем `admin.site.register(...)`

Пример — `apps/workflow/applications/admin.py`:

```python
"""Admin для приложения applications (T-3-005, ранее application/admin.py)."""
from django.contrib import admin

from apps.workflow.applications.models import Application, ApplicationStatus, ApplicationEvent


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'display', 'panel', 'status', 'last_update_date_time')
    list_filter = ('status', 'display__city')
    search_fields = ('display__description', 'panel__name', 'id')
    ordering = ('-last_update_date_time',)
    
    fields = [
        ('display', 'panel', 'cell', 'status'),
        # ВАЖНО: 28 денормализованных полей будут УДАЛЕНЫ в T-2-021!
        # Сейчас перечислены для compatибельности, в T-2-021 этот блок удаляется.
        ('comment_monitoring', 'time_monitoring', 'file_monitoring'),
        ('comment_control_apply', 'time_control_apply', 'file_control_apply'),
        ('comment_control_send', 'time_control_send', 'file_control_send'),
        ('comment_service_apply', 'time_service_apply', 'file_service_apply'),
        ('comment_control_at_work', 'time_control_at_work', 'file_control_at_work'),
        ('comment_control_unable', 'time_control_unable', 'file_control_unable'),
        ('comment_control_archive', 'time_control_archive', 'file_control_archive'),
        # После T-2-021 этот блок УДАЛЯЕТСЯ, добавляется:
        # 'last_update_date_time',
    ]


@admin.register(ApplicationStatus)
class ApplicationStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')


@admin.register(ApplicationEvent)
class ApplicationEventAdmin(admin.ModelAdmin):
    """Read-only — записи только через ActivityLogger."""
    list_display = ('id', 'application', 'event_type', 'actor_username', 'occurred_at', 'state_to')
    list_filter = ('event_type',)
    search_fields = ('application__id', 'actor_username', 'comment')
    date_hierarchy = 'occurred_at'
    readonly_fields = tuple(f.name for f in ApplicationEvent._meta.fields)
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
```

### Шаг 3. Удалить регистрации в legacy admin'ках

После того как новый admin зарегистрирован, **legacy admin.py надо опустошить** (но не удалить файл — Django apps autodiscover ищет admin.py):

`application/admin.py`:
```python
"""
T-3-005: admin перенесён в apps.workflow.applications.admin.
Этот файл оставлен пустым ради app autodiscover.
"""
```

То же для `zip/admin.py`, `departure/admin.py`, `main/admin.py`, `user/admin.py`, `main_menu/admin.py`.

### Шаг 4. Contact admin — финальное место

В `apps/workflow/departures/admin.py`:

```python
@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'description', 'phone_number')
    search_fields = ('first_name', 'last_name', 'description', 'phone_number')
    list_filter = ('displays',)
    filter_horizontal = ('displays',)
```

`filter_horizontal` — стандартная Django UX для M2M, удобнее чем `filter_vertical`.

### Шаг 5. Проверка

```bash
python manage.py check
# ожидание: чисто

python manage.py runserver
# открыть http://localhost:8000/admin/
# ожидание: 
#   - Все ранее доступные модели на месте
#   - Никаких 500 на /admin/ страницах
#   - Грубо: число моделей до и после = одинаково (или больше — если ApplicationEvent добавили)

# Smoke на ключевых страницах:
# /admin/workflow_applications/application/
# /admin/workflow_departures/contact/
# /admin/directory_panels/panel/
# /admin/directory_displays/display/
```

---

## Критерии приёмки

- [ ] Все admin-классы перенесены в соответствующие `apps/*/admin.py`
- [ ] Legacy admin.py'ы опустошены (но файл существует)
- [ ] Не используется `from <legacy>.models import *` — везде явные импорты
- [ ] `python manage.py check` — чисто
- [ ] Все админки доступны через `/admin/` без 500 ошибок
- [ ] `ApplicationEventAdmin` — read-only (нельзя добавить вручную)
- [ ] Comment в `ApplicationAdmin.fields` указывает, что блок удаляется в T-2-021
- [ ] Smoke-test всех ключевых admin-страниц прошёл

---

## Что НЕ делать

- **НЕ удаляй** legacy admin.py файлы — autodiscover их ищет, при отсутствии будет warning
- **НЕ переноси** `mail/admin.py` — это интеграция Фазы 5
- **НЕ удаляй** упоминания удалённых полей в `fields=[...]` — оставь, в T-2-021 одним коммитом удалим
- **НЕ меняй** `list_display` (это UX, не задача рефакторинга)

---

## Что закрывается этой задачей

- ✅ Баг B2 из ревью архитектора Фазы 2
- ✅ Подготовка к чистому удалению legacy в Фазе 4
