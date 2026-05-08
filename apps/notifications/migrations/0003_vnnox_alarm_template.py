from django.db import migrations


TEMPLATE = {
    "name": "vnnox_alarm_unresolved",
    "description": "VNNOX-аларм не восстановился за threshold",
    "text": (
        "VNNOX-аларм висит {minutes} мин.\n"
        "Экран: {display_description}\n"
        "Ячейка: {cell_position}\n"
        "{raw_position}"
    ),
}


def forwards(apps, _schema_editor):
    template_model = apps.get_model("notifications", "NotificationTemplate")
    template_model.objects.update_or_create(name=TEMPLATE["name"], defaults=TEMPLATE)


class Migration(migrations.Migration):
    dependencies = [("notifications", "0002_seed_templates")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
