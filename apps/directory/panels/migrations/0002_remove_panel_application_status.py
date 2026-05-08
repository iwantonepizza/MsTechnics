"""
T-2-028: удаляем денормализованное поле application_status из Panel.
Статус вычисляется через Panel.application_status property или QuerySet.with_application_status().

ВАЖНО: применять после того, как весь код перестал писать в panel.application_status.
После применения — убедиться что шаблоны используют annotation, а не property (N+1).
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("directory_panels", "0001_initial_state_import"),
        ("workflow_applications", "0001_initial_state_import"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="panel",
            name="application_status",
        ),
    ]
