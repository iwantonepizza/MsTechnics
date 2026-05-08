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
                    name="DailyTask",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("name", models.CharField(max_length=20, unique=True, verbose_name='название"')),
                        ("description", models.TextField(blank=True, verbose_name="описание")),
                        ("status", models.CharField(choices=[("not_ready", "Не готово"), ("ready", "Доступно"), ("deadline", "Дедлайн"), ("done", "Выполнено"), ("undone", "Не выполнено")], db_column="Статус", default="undone", max_length=20, verbose_name="Статус")),
                        ("start_time", models.TimeField(blank=True, null=True, verbose_name="начало")),
                        ("end_time", models.TimeField(blank=True, null=True, verbose_name="конец")),
                        ("link", models.URLField(max_length=150, verbose_name="ссылка")),
                        ("last_completed_date", models.DateField(blank=True, null=True, verbose_name="уведомление выполнение")),
                        ("alert_notification_sent", models.BooleanField(default=False, verbose_name="уведомление скорое начало")),
                        ("deadline_notification_sent", models.BooleanField(default=False, verbose_name="уведомление дедлайн")),
                        ("lost_notification_sent", models.BooleanField(default=False, verbose_name="уведомление пропуск")),
                        ("start_notification_sent", models.BooleanField(default=False, verbose_name="уведомление начало")),
                        ("completed_notification_sent", models.BooleanField(default=False, verbose_name="уведомление выполнение")),
                        ("city", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="core_references.cities", verbose_name="Город")),
                    ],
                    options={"db_table": "daily_task", "verbose_name": "Задание", "verbose_name_plural": "Задания"},
                ),
            ],
        ),
    ]
