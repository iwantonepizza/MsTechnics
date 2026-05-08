from django.db import migrations


TEMPLATES = [
    {
        "name": "application_created",
        "description": "Новая заявка появилась в очереди контроля",
        "text": "Новая заявка ID-{application_id} на экране {display_description} ({cell_position})\n\n{comment}",
    },
    {
        "name": "application_assigned_to_executor",
        "description": "Заявка отправлена в сервис, назначен исполнитель",
        "text": "Тебе назначена заявка ID-{application_id}\n\n{display_description}, {cell_position}\n{comment}",
    },
    {
        "name": "application_completed",
        "description": "Заявка выполнена",
        "text": "Заявка ID-{application_id} на {display_description} выполнена.\nИсполнитель: {executor_name}",
    },
    {
        "name": "departure_assigned",
        "description": "Назначен выезд",
        "text": "Назначен выезд: {departure_date}\n{description}\nЗаявки: {applications_count}",
    },
    {
        "name": "application_sla_overdue",
        "description": "Заявка просрочена SLA",
        "text": "ID-{application_id} висит {hours_overdue} ч в статусе {current_status}",
    },
    {
        "name": "daily_task_overdue",
        "description": "Ежедневная задача не выполнена",
        "text": "Ежедневная задача \"{task_name}\" не выполнена",
    },
]


def forwards(apps, _schema_editor):
    template_model = apps.get_model("notifications", "NotificationTemplate")
    for template in TEMPLATES:
        template_model.objects.update_or_create(name=template["name"], defaults=template)


class Migration(migrations.Migration):
    dependencies = [("notifications", "0001_initial")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
