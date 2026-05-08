from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("workflow_applications", "0001_initial_state_import"),
        ("directory_displays", "0001_initial_state_import"),
        ("directory_panels", "0001_initial_state_import"),
        ("workflow_departures", "0001_initial_state_import"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="application",
                    name="cell",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="directory_displays.cell",
                        verbose_name="Ячейка",
                    ),
                ),
                migrations.AddField(
                    model_name="application",
                    name="display",
                    field=models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="application",
                        to="directory_displays.display",
                        to_field="name",
                        verbose_name="Экран",
                    ),
                ),
                migrations.AddField(
                    model_name="application",
                    name="executor",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="workflow_departures.executor",
                        verbose_name="Исполнитель",
                    ),
                ),
                migrations.AddField(
                    model_name="application",
                    name="panel",
                    field=models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="application",
                        to="directory_panels.panel",
                        to_field="name",
                        verbose_name="Панель",
                    ),
                ),
            ],
        ),
    ]
