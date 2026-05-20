from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workflow_departures", "0004_alter_departure_options_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="departure",
                    name="status_legacy",
                    field=models.CharField(
                        blank=True,
                        db_column="status",
                        default="",
                        max_length=40,
                        verbose_name="Статус (legacy, удалить после backfill)",
                    ),
                ),
            ],
        ),
    ]
