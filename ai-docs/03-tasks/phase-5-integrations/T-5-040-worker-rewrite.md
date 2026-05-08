# T-5-040 / T-5-041 / T-5-042. Worker stack rewrite + structlog + Sentry

> **Тип:** infra / cleanup
> **Приоритет:** P1
> **Оценка:** 4 часа (2 + 1.5 + 0.5)
> **Фаза:** 5
> **Статус:** review
> **Взял:** GPT-5 Codex

---

## Зависимости

- **Блокируется:** T-2-fix-002 (DailyTask на месте), T-5-006 (triggers)
- **Блокирует:** T-5-050+ (legacy cleanup)

---

## T-5-040. daily_checker.py → django-q2 / cron

### Что есть

`daily_checker.py` (legacy, корень проекта) — отдельный worker, infinite loop, проверяет `DailyTask` и шлёт уведомления через Redis pubsub.

### Что сделать

**Подход A: Management command + cron (проще, рекомендуется)**

```python
# apps/workflow/daily_tasks/management/commands/check_daily_tasks.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.workflow.daily_tasks.models import DailyTask
from apps.notifications.services import notification_dispatcher
from apps.notifications.models import Notification, NotificationTemplate


class Command(BaseCommand):
    help = 'Проверяет DailyTask и шлёт уведомления о просроченных'
    
    def handle(self, *args, **opts):
        now = timezone.now()
        
        overdue = DailyTask.objects.filter(
            status='not_ready',
            deadline__lt=now,
        ).select_related('user_assigned')
        
        template = NotificationTemplate.objects.get(name='daily_task_overdue')
        
        for task in overdue:
            stage = f'overdue_{now.date()}'
            if stage in (task.notified_stages or []):
                continue
            
            if not task.user_assigned:
                continue
            
            notif = Notification.objects.create(
                template=template,
                recipient=task.user_assigned,
                rendered_text=template.text.format(task_name=task.name),
                related_target=task,
            )
            notification_dispatcher.dispatch(notif)
            
            # Mark notified
            task.notified_stages = [*(task.notified_stages or []), stage]
            task.save(update_fields=['notified_stages'])
```

Cron:
```cron
0 8,12,16,20 * * * cd /opt/mstechnics && /opt/venv/bin/python manage.py check_daily_tasks
```

**Подход B: django-q2 (если хочется in-app scheduler)**

```bash
pip install django-q2
```

`config/settings.py`:
```python
INSTALLED_APPS += ['django_q']
Q_CLUSTER = {
    'name': 'mstech',
    'workers': 2,
    'recycle': 500,
    'timeout': 60,
    'redis': {'host': 'redis', 'port': 6379},
}
```

Schedule:
```python
# apps/workflow/daily_tasks/apps.py
def ready(self):
    from django_q.tasks import schedule, Schedule
    schedule(
        'apps.workflow.daily_tasks.tasks.check_overdue',
        schedule_type=Schedule.HOURLY,
    )
```

**Рекомендация:** **Подход A** — cron надёжнее и проще. django-q2 даст бонус только если нужны async-задачи с retry'ами.

### Удалить legacy

```bash
git rm daily_checker.py
```

Обновить `docker-compose.yml` — убрать service `daily_checker`. Cron — отдельный systemd timer / cron container.

### Критерии T-5-040

- [x] `check_daily_tasks` management command работает
- [x] Cron/systemd timer config запускает регулярную проверку
- [x] Идемпотентность через `notified_stages`
- [x] daily_checker.py удалён, docker-compose обновлён

---

## T-5-041. ManageControl.py удалить

### Что есть

`ManageControl.py` — оркестратор, запускающий worker'ы (вероятно tg_sender + daily_checker через subprocess).

### Что сделать

**После закрытия T-5-011 + T-5-040:**

1. Worker'ов больше нет (TG ушёл в triggers, daily_checker — в cron).
2. `ManageControl.py` больше не нужен.

```bash
git rm ManageControl.py
```

### docker-compose минимальный

```yaml
version: '3.9'
services:
  postgres:
    image: postgres:16-alpine
    # ...
  
  redis:
    image: redis:7-alpine
  
  django:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
    depends_on: [postgres, redis]
  
  cron:
    build: .
    command: /usr/sbin/cron -f
    depends_on: [postgres, redis]
    # cron внутри контейнера запускает manage.py команды
  
  # frontend (после T-4 build)
  nginx:
    image: nginx:alpine
    # ... reverse proxy + serve frontend dist
```

### Критерии T-5-041

- [x] ManageControl.py удалён
- [x] docker-compose чистый
- [x] systemd timers с правильными командами

---

## T-5-042. structlog + Sentry в воркеры

### structlog

**Уже есть** в основном Django через `config/settings.py`. Но в management commands и в `apps/notifications/channels/*` тоже надо использовать.

**Что проверить:**

```bash
grep -rn "import logging" apps/ | head -10
# Если есть `import logging` — заменять на structlog где это новый код
```

В каждом новом модуле:
```python
import structlog
logger = structlog.get_logger(__name__)

logger.info('event_name', key1=value1, key2=value2)
```

### Sentry

```bash
pip install sentry-sdk
```

`config/settings.py`:
```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

if SENTRY_DSN := env('SENTRY_DSN', default=None):
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        traces_sample_rate=0.05,  # 5% профайлинг
        send_default_pii=False,   # не шлём username/email/etc
        environment=env('SENTRY_ENV', default='development'),
        release=env('GIT_COMMIT', default='dev'),
    )
```

### Критерии T-5-042

- [ ] structlog в `apps/notifications/`, `apps/integrations/gmail_alarms/`
- [ ] Sentry настроен через env (опционально, можно отложить если DSN ещё нет)
- [ ] Тесты: `caplog` структурированных логов

---

## Что НЕ делать

- НЕ ставить Celery — overkill для нашего объёма
- НЕ хранить SENTRY_DSN в репо
- НЕ запускать management команды в Django ASGI process — отдельный cron-контейнер
