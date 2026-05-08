# T-5-050 / T-5-051 / T-5-052 / T-5-053. Legacy cleanup — templates, views, shims, MsServiceControl

> **Тип:** cleanup
> **Приоритет:** P2
> **Оценка:** 4.5 часа (1 + 2 + 1 + 0.5)
> **Фаза:** 5
> **Статус:** blocked (после деплоя SPA на staging и 2 недель работы без инцидентов)

---

## Зависимости

- **Блокируется:** Фаза 4 закрыта, SPA в проде минимум 2 недели без откатов
- **Блокирует:** ничего (это финальная задача)

---

## Контекст

После Фазы 4 фронт работает через SPA → REST API. Legacy Django views + templates становятся ненужными. Но **не удалять резко** — оставить пока SPA на staging стабилизируется.

---

## T-5-050. Удалить legacy templates

### Что удалить

```
templates/                    # все .html файлы
├── application/
├── control/
├── departure/
├── main/
├── main_menu/
├── monitoring/
├── service/
├── user/
└── zip/
```

`static/` — оставить пока (файлы и медиа). После полной проверки — удалить static/'ы legacy.

### Шаги

```bash
git rm -r templates/
```

Settings:
```python
# config/settings.py
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],  # пусто
    'APP_DIRS': True,  # для admin templates
    # ...
}]
```

### Smoke

```bash
python manage.py check
python manage.py runserver
# /admin/ работает (его шаблоны в admin app)
# /api/v1/me работает
# /menu — 404 (legacy view удалён в T-5-051)
```

### Критерии

- [ ] `templates/` удалена
- [ ] `python manage.py check` чисто
- [ ] /admin/ работает

---

## T-5-051. Удалить legacy views и URLs

### Что удалить

`config/urls.py` — убрать legacy include'ы:

```python
# БЫЛО
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.interface.api.v1.urls')),
    path('api/schema/', SpectacularAPIView.as_view()),
    
    # Legacy:
    path('', include('main_menu.urls')),
    path('user/', include('user.urls')),
    path('monitoring/', include('monitoring.urls')),
    path('control/', include('control.urls')),
    path('service/', include('service.urls')),
    path('zip/', include('zip.urls')),
    path('application/', include('application.urls')),
    path('departure/', include('departure.urls')),
    path('mail/', include('mail.urls')),
]

# СТАЛО
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.interface.api.v1.urls')),
    path('api/schema/', SpectacularAPIView.as_view()),
    # Frontend serving:
    re_path(r'^.*$', FrontendView.as_view()),  # SPA fallback (или nginx)
]
```

### Удалить директории

```bash
git rm -r main_menu/views.py main_menu/urls.py main_menu/templatetags/  # оставить только models.py если надо
git rm -r monitoring/  # вся
git rm -r control/
git rm -r service/
git rm -r application/views.py application/urls.py
git rm -r departure/views.py departure/urls.py
git rm -r user/views.py user/urls.py user/forms.py
git rm -r zip/views.py zip/urls.py
git rm -r mail/views.py mail/urls.py mail/forms.py
```

**ВАЖНО:** не удалять полностью `application/`, `departure/`, `user/`, `zip/`, `main/`, `mail/`, `main_menu/` — там остаются:
- compat-shims в `models.py` (T-5-052 удалит)
- `migrations/` (нельзя удалить, там история)

### Smoke

```bash
python manage.py check
# чисто

# Все API эндпоинты работают
curl /api/v1/me/  # 401 unauthorized — ОК

# Legacy URLs больше не обслуживаются
curl /menu  # 404 (или попадает в SPA fallback)
```

### Критерии

- [ ] Legacy views.py / urls.py / forms.py удалены
- [ ] config/urls.py чистый
- [ ] /admin/ работает
- [ ] /api/v1/* работает
- [ ] python manage.py check чисто

---

## T-5-052. Удалить compat-shims

### Что есть

После Фазы 2 модели переехали в `apps/`, но остались re-export shim'ы:

```python
# main/models.py
from apps.core.references.models import Color, Cities, Smile, Condition  # noqa: F401

# user/models.py
from apps.core.users.models import MsUser  # noqa: F401

# zip/models.py
from apps.directory.displays.models import Display, Cell  # noqa: F401
from apps.directory.panels.models import Panel, Department  # noqa: F401
from apps.directory.storage.models import Wires, Hubs, Lamels  # noqa: F401
from apps.workflow.daily_tasks.models import DailyTask  # noqa: F401
Panels = Panel  # legacy alias

# application/models.py
from apps.workflow.applications.models import Application, ApplicationStatus, ApplicationEvent  # noqa: F401

# departure/models.py
from apps.workflow.departures.models import Contact, Departure, DepartureHistoryReport, Executor  # noqa: F401
```

### Что сделать

**Шаг 1. Verify нет references**

```bash
# Из non-migration кода
grep -rln "from main.models\|from user.models\|from zip.models\|from application.models\|from departure.models" \
  --include='*.py' apps/ shared/ tests/ frontend/  # пусто должно быть

# Если что-то найдено — заменить на новый путь
# Например: from main.models → from apps.core.references.models
```

**Шаг 2. Verify migrations не ломаются**

В migrations может быть `('zip', 'XXXX_initial')` зависимости — это **OK**, оставляем. Но импортов `from zip.models import ...` в миграциях быть **не должно**.

```bash
grep -rln "from \(main\|user\|zip\|application\|departure\)\.models" --include='*.py' apps/*/migrations/ */migrations/
# должно быть пусто
```

**Шаг 3. Опустошить shim'ы**

Не удалять файлы целиком — оставить пустые с комментарием:

```python
# main/models.py
"""T-5-052: модели переехали в apps.core.references. Shim очищен."""
```

**Шаг 4. Удалить admin.py legacy**

```bash
# Эти файлы пустые после T-3-005 — удалить
git rm main/admin.py user/admin.py zip/admin.py application/admin.py departure/admin.py main_menu/admin.py mail/admin.py
```

**Шаг 5. Проверить INSTALLED_APPS**

В `config/settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'apps.core',
    'apps.directory',
    'apps.workflow',
    'apps.activity',
    'apps.notifications',
    'apps.integrations',
    'apps.interface',
    
    # Legacy — оставить, иначе миграции ломаются:
    'application',
    'departure',
    'mail',
    'main',
    'main_menu',
    'monitoring',  # если ещё есть
    'service',     # если ещё есть
    'user',
    'zip',
    'control',     # если ещё есть
]
```

Legacy apps **остаются в INSTALLED_APPS** — потому что они владеют migrations. Если убрать — Django запутается в state.

### Критерии T-5-052

- [ ] `grep -rn "from main.models\|from zip.models\|from user.models" --include='*.py' apps/ shared/ tests/` — пусто
- [ ] Shim файлы пустые (или удалены)
- [ ] Legacy admin.py удалены
- [ ] `python manage.py check` — чисто
- [ ] `python manage.py makemigrations --dry-run` — пусто

---

## T-5-053. Удалить MsServiceControl/

### Что есть

После T-2-010 `MsServiceControl/` → `config/`. Если остались:
- `MsServiceControl/` — старая Django settings папка (должна быть удалена в Фазе 2)

### Что сделать

```bash
# Проверить:
ls -la MsServiceControl/  # если есть и не пусто — что-то осталось

# Если только __pycache__:
git rm -r MsServiceControl/

# Если есть нужные файлы — переехать в config/ или scripts/
```

Также:
- `Config/` (если есть с большой буквы и не нужно) — проверить и решить
- `ManageControl.py` (T-5-041 удалит)

### Критерии T-5-053

- [ ] `MsServiceControl/` удалена
- [ ] `Config/` проверено и удалено / переименовано
- [ ] Нет лишних файлов в корне репо

---

## После всего — финальная инвентаризация

После T-5-050..053 структура проекта должна быть:

```
mstechnics/
├── AGENTS.md
├── HANDOFF.md
├── README.md
├── pyproject.toml
├── requirements.lock
├── .env.example
├── manage.py
├── docker-compose.yml
├── Dockerfile
│
├── config/                     # Django settings
├── apps/                       # все доменные приложения
│   ├── core/
│   ├── directory/
│   ├── workflow/
│   ├── activity/
│   ├── notifications/
│   ├── integrations/
│   └── interface/
│
├── shared/                     # cross-cutting helpers
│
├── frontend/                   # React SPA
│
├── ai-docs/                    # архитектурная документация
│
├── scripts/                    # bash утилиты
├── fixtures/                   # data seeds
├── media/                      # uploaded files
├── static/                     # collected static (admin)
│
├── application/                # legacy app, ТОЛЬКО migrations + пустой models.py
├── main/                       # ditto
├── user/                       # ditto
├── zip/                        # ditto
├── departure/                  # ditto
├── main_menu/                  # ditto
├── mail/                       # ditto
├── monitoring/                 # ditto
├── service/                    # ditto
└── control/                    # ditto
```

И когда после долгого выполнения миграций (например, через год+) — все old migrations можно squash'нуть и удалить legacy apps. Но это **не задача Фазы 5**.

---

## Что НЕ делать

- НЕ удалять migrations/ старых apps — это история, без них новый dev не поднимется
- НЕ удалять `__init__.py` из legacy apps — Django apps autodiscover сломается
- НЕ удалять до 2-недельной работы SPA в staging без инцидентов
