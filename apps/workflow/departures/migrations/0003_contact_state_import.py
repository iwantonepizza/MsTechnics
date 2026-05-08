from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workflow_departures", "0002_departure_status_fk"),
        ("directory_displays", "0001_initial_state_import"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Contact",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("first_name", models.CharField(blank=True, max_length=150, verbose_name="Имя")),
                        ("last_name", models.CharField(blank=True, max_length=150, verbose_name="Фамилия")),
                        ("description", models.CharField(blank=True, max_length=150, verbose_name="Описание")),
                        ("phone_number", models.CharField(blank=True, max_length=15, null=True, verbose_name="Телефон")),
                        ("telegram_id", models.CharField(blank=True, max_length=15, null=True, verbose_name="Telegram ID")),
                        ("displays", models.ManyToManyField(blank=True, related_name="contacts", to="directory_displays.display", verbose_name="Список экранов")),
                    ],
                    options={"db_table": "contact", "verbose_name": "Контакт", "verbose_name_plural": "Контакты", "ordering": ["id"]},
                ),
            ],
        ),
    ]
