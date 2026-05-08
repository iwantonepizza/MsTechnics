"""
T-2-029: добавляем notified_stages JSONField вместо 5 булевых полей.

Старые поля (alert_notification_sent, deadline_notification_sent, etc.)
оставляем для обратной совместимости. Удалим в отдельной миграции после
переключения всего кода на notified_stages.
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("zip", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailytask",
            name="notified_stages",
            field=models.JSONField(
                default=list,
                blank=True,
                verbose_name="Отправленные уведомления",
                help_text=(
                    "Список отправленных стадий: ['alert', 'start', 'deadline', 'lost', 'completed']. "
                    "Заменяет 5 булевых полей *_notification_sent."
                ),
            ),
        ),
    ]
