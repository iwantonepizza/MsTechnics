# T-5-006. Triggers — 6 правил уведомлений

> **Тип:** business / signals
> **Приоритет:** P0
> **Оценка:** 2 часа
> **Фаза:** 5
> **Статус:** done
> **Взял:** GPT-5 Codex

---

## Цель

Привязать уведомления к доменным событиям. Когда заявка создаётся / переводится / выезд назначается / SLA-просрочена — соответствующие пользователи получают уведомление.

---

## Зависимости

- **Блокируется:** T-5-001 (Notification model + dispatcher)
- **Блокирует:** ничего

---

## 6 правил

| # | Триггер | Кто получает | Шаблон |
|---|---|---|---|
| 1 | Заявка создана (status=`sent_to_control`) | Все юзеры с `permission='control'` или `'admin'` в этом городе | "Новая заявка ID-{id} на экране {display}: {comment_short}" |
| 2 | Заявка отправлена в сервис (status=`sent_to_service`, executor назначен) | Назначенный `executor.user_id` | "Тебе назначена заявка ID-{id} на {display} ({cell}): {comment_short}" |
| 3 | Заявка выполнена (status=`done`) | Создатель (user_monitoring), все control в городе | "Заявка ID-{id} выполнена. {executor} починил." |
| 4 | Выезд назначен (Departure created) | Назначенные executor'ы | "Тебе выезд завтра в {city}, {N} заявок" |
| 5 | SLA-просрочено (создан > 4 часов назад, статус не done/archive) | Юзер `permission='control'` в городе | "ID-{id} висит {hours_overdue}ч, разберись" |
| 6 | DailyTask просрочена | Назначенный пользователь | "Ежедневная задача '{task.name}' не выполнена" |

---

## Что сделать

### Шаг 1. Структура

```
apps/notifications/triggers/
├── __init__.py
├── application.py    # rules 1, 2, 3
├── departure.py      # rule 4
├── sla.py            # rule 5
└── daily.py          # rule 6
```

### Шаг 2. Шаблоны

Создать data-migration для seed'а NotificationTemplate'ов:

```python
# apps/notifications/migrations/00XX_seed_templates.py

TEMPLATES = [
    {
        'name': 'application_created',
        'description': 'Новая заявка появилась в очереди контроля',
        'text': 'Новая заявка <b>ID-{application_id}</b> на экране {display_description} ({cell_position})\n\n{comment}',
    },
    {
        'name': 'application_assigned_to_executor',
        'description': 'Заявка отправлена в сервис, назначен исполнитель',
        'text': 'Тебе назначена заявка <b>ID-{application_id}</b>\n\n{display_description}, {cell_position}\n{comment}',
    },
    {
        'name': 'application_completed',
        'description': 'Заявка выполнена',
        'text': 'Заявка <b>ID-{application_id}</b> на {display_description} выполнена.\nИсполнитель: {executor_name}',
    },
    {
        'name': 'departure_assigned',
        'description': 'Назначен выезд',
        'text': 'Выезд: <b>{departure_date}</b>\n{display_description}, {city_name}\nЗаявки: {applications_count}',
    },
    {
        'name': 'application_sla_overdue',
        'description': 'Заявка просрочена SLA',
        'text': '⚠️ <b>ID-{application_id}</b> висит {hours_overdue} часов в статусе {current_status}',
    },
    {
        'name': 'daily_task_overdue',
        'description': 'Ежедневная задача не выполнена',
        'text': '🔔 Ежедневная задача "{task_name}" не выполнена',
    },
]


def forwards(apps, _):
    Tpl = apps.get_model('notifications', 'NotificationTemplate')
    for t in TEMPLATES:
        Tpl.objects.update_or_create(name=t['name'], defaults=t)


class Migration(migrations.Migration):
    dependencies = [('notifications', '0001_initial')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
```

### Шаг 3. Trigger'ы — application

```python
# apps/notifications/triggers/application.py
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.workflow.applications.models import Application
from apps.notifications.services import notification_dispatcher
from apps.notifications.models import Notification, NotificationTemplate


@receiver(post_save, sender=Application)
def on_application_saved(sender, instance: Application, created, update_fields, **kwargs):
    """Маршрутизатор по новому статусу."""
    if created and instance.status.name == 'sent_to_control':
        _trigger_application_created(instance)
        return
    
    # Statu changed?
    if 'status' not in (update_fields or ()):
        return
    
    if instance.status.name == 'sent_to_service' and instance.executor_id:
        _trigger_application_assigned(instance)
    elif instance.status.name == 'done':
        _trigger_application_completed(instance)


def _trigger_application_created(app: Application):
    """Уведомить всех контролёров в городе экрана."""
    from apps.core.users.models import MsUser
    
    template = NotificationTemplate.objects.get(name='application_created')
    
    # Контролёры этого города
    recipients = MsUser.objects.filter(
        permission__in=['control', 'admin', 'all'],
        allowed_city=app.display.city,
    ).distinct()
    
    context = {
        'application_id': app.id,
        'display_description': app.display.description,
        'cell_position': app.cell.position if app.cell else '—',
        'comment': (app.comment_monitoring or '')[:200],
    }
    
    for user in recipients:
        notification = Notification.objects.create(
            template=template,
            recipient=user,
            rendered_text=template.text.format(**context),
            context=context,
            related_target=app,
        )
        notification_dispatcher.dispatch(notification)


def _trigger_application_assigned(app: Application):
    """Уведомить назначенного исполнителя."""
    if not (app.executor and app.executor.user):
        return
    
    template = NotificationTemplate.objects.get(name='application_assigned_to_executor')
    context = {
        'application_id': app.id,
        'display_description': app.display.description,
        'cell_position': app.cell.position if app.cell else '—',
        'comment': (app.comment_control_send or app.comment_monitoring or '')[:200],
    }
    notification = Notification.objects.create(
        template=template,
        recipient=app.executor.user,
        rendered_text=template.text.format(**context),
        context=context,
        related_target=app,
    )
    notification_dispatcher.dispatch(notification)


def _trigger_application_completed(app: Application):
    """Уведомить создателя + контролёров."""
    # ... аналогично
    pass
```

### Шаг 4. Подключить signals

В `apps/notifications/apps.py`:

```python
class NotificationsConfig(AppConfig):
    name = 'apps.notifications'
    
    def ready(self):
        # Импортируем триггеры — это включает receiver-сигналы
        from .triggers import application, departure, daily, sla  # noqa
```

### Шаг 5. SLA + Daily — через cron / management command

Эти триггеры не сигнальные, а периодические:

```python
# apps/notifications/management/commands/check_sla.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from apps.workflow.applications.models import Application
from apps.notifications.models import Notification, NotificationTemplate
from apps.notifications.services import notification_dispatcher


class Command(BaseCommand):
    help = 'Проверяет заявки и шлёт уведомления о SLA-просрочке'
    
    def handle(self, *args, **opts):
        # SLA: 4 часа в одном из статусов
        threshold = timezone.now() - timedelta(hours=4)
        
        overdue = Application.objects.filter(
            status__name__in=['sent_to_control', 'apply_in_control', 'sent_to_service', 'work_in_service'],
            last_update_date_time__lt=threshold,
        )
        
        for app in overdue:
            # Idempotency: не шлём дважды один и тот же sla-alert за день
            already_sent = Notification.objects.filter(
                related_target_ct__model='application',
                related_target_id=str(app.id),
                template__name='application_sla_overdue',
                sent_at__date=timezone.now().date(),
            ).exists()
            if already_sent:
                continue
            
            # ... создать notification и dispatch
```

Запуск из cron'а:
```cron
*/15 * * * * cd /opt/mstechnics && python manage.py check_sla
0 8,14,20 * * * cd /opt/mstechnics && python manage.py check_daily_tasks
```

(Или через django-q2 schedule, если решим использовать его — см. T-5-040.)

---

## Критерии приёмки

- [ ] 6 templates seeded в БД
- [ ] Triggers подключены через AppConfig.ready()
- [ ] Application created → notification отправляется всем control в городе
- [ ] Application assigned → notification только executor'у
- [ ] SLA management command работает
- [ ] Daily Task management command работает
- [ ] Idempotency: SLA-уведомление не шлётся дважды в день
- [ ] Тесты на каждый trigger (минимум 6)

---

## Что НЕ делать

- НЕ слать уведомление если recipient — сам инициатор изменения
- НЕ блокировать save() — если dispatch падает, application всё равно сохраняется (try/except в trigger)
- НЕ хардкодить "control" — через role-based фильтрацию
