"""T-2-013: импортируем существующие таблицы panel, department."""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("core_references", "0001_initial_state_import"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Panel",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("name", models.CharField(max_length=15, unique=True, verbose_name="идентификатор")),
                        ("comment", models.TextField(blank=True, null=True, verbose_name="описание")),
                        ("display", models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to="directory_displays.display", to_field="name", verbose_name="установлен на")),
                        ("condition", models.ForeignKey(default="work", null=True, on_delete=django.db.models.deletion.PROTECT, to="core_references.condition", to_field="name", verbose_name="состояние")),
                        ("department", models.ForeignKey(default="zip", null=True, on_delete=django.db.models.deletion.PROTECT, to="core_references.department", to_field="name", verbose_name="нахождение")),
                        # application_status пока оставляем в state — удалим в 0002
                        ("application_status", models.ForeignKey(default="default", null=True, on_delete=django.db.models.deletion.PROTECT, to="workflow_applications.applicationstatus", to_field="name", verbose_name="статус заявки")),
                    ],
                    options={"db_table": "panel", "verbose_name": "Панель", "ordering": ["id"]},
                ),
            ],
        ),
    ]
