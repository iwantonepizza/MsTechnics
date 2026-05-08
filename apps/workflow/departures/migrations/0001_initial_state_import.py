"""T-2-014: импортируем существующие таблицы departure, executor."""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [("user", "0001_initial_state_import")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Executor",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("first_name", models.CharField(blank=True, max_length=150, verbose_name="Имя")),
                        ("last_name", models.CharField(blank=True, max_length=150, verbose_name="Фамилия")),
                        ("executor_role", models.CharField(default="должности нет", max_length=20, verbose_name="Должность")),
                        ("phone_number", models.CharField(blank=True, max_length=15, null=True, verbose_name="Телефон")),
                        ("telegram_id", models.CharField(blank=True, max_length=20, null=True, verbose_name="Telegram ID")),
                    ],
                    options={"db_table": "executor", "verbose_name": "Исполнитель", "ordering": ["id"]},
                ),
                migrations.CreateModel(
                    name="Departure",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("description", models.TextField(blank=True, null=True, verbose_name="Описание")),
                        ("user_create", models.CharField(max_length=20, verbose_name="Создатель")),
                        ("time_updated", models.DateTimeField(blank=True, null=True)),
                        ("time_created", models.DateTimeField(blank=True, null=True)),
                        ("time_start", models.DateTimeField(blank=True, null=True)),
                        ("time_end", models.DateTimeField(blank=True, null=True)),
                        ("result", models.TextField(blank=True, null=True, verbose_name="Результат")),
                        ("notification", models.JSONField(blank=True, null=True)),
                        # legacy CharField — существующая колонка в БД
                        ("status_legacy", models.CharField(blank=True, db_column="status", default="", max_length=40, verbose_name="Статус (legacy)")),
                        ("executor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="workflow_departures.executor", verbose_name="Исполнитель")),
                    ],
                    options={"db_table": "departure", "verbose_name": "Выезд", "ordering": ["id"]},
                ),
                migrations.CreateModel(
                    name="DepartureHistoryReport",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("description", models.TextField(blank=True, null=True)),
                        ("comment", models.TextField(verbose_name="Комментарий")),
                        ("time", models.DateTimeField(verbose_name="Время")),
                        ("departure", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to="workflow_departures.departure", verbose_name="Выезд")),
                        ("user", models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to="user.msuser", verbose_name="Работник")),
                    ],
                    options={"db_table": "departure_history_report", "ordering": ["id"]},
                ),
            ],
        ),
    ]
