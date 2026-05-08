from django.db import migrations


TEMPLATE = {
    "name": "legacy_message",
    "description": "Compat-шаблон для legacy presend_filters",
    "text": "{text}",
}


def forwards(apps, _schema_editor):
    template_model = apps.get_model("notifications", "NotificationTemplate")
    template_model.objects.update_or_create(name=TEMPLATE["name"], defaults=TEMPLATE)


class Migration(migrations.Migration):
    dependencies = [("notifications", "0003_vnnox_alarm_template")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
