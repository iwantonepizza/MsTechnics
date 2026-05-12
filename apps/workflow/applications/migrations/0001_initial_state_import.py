"""
T-2-014: импортируем существующие таблицы application, application_status, history_application.
T-2-020: создаём новую таблицу application_event.
"""
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("core_references", "0001_initial_state_import"),
        ("user", "0001_initial_state_import"),
        ("application", "0003_initial"),
    ]

    operations = [
        # Импортируем существующие таблицы
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="ApplicationStatus",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("name", models.TextField(max_length=40, unique=True, verbose_name="название")),
                        ("description", models.TextField(blank=True, null=True, verbose_name="описание")),
                        ("color", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="application_status_color", to="core_references.color", verbose_name="цвет")),
                        ("color_text", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="application_status_color_text", to="core_references.color", verbose_name="цвет текста")),
                        ("icon", models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to="core_references.smile", verbose_name="иконка")),
                    ],
                    options={"db_table": "application_status", "verbose_name": "Статус заявки", "ordering": ["id"]},
                ),
                migrations.CreateModel(
                    name="ApplicationHistoryReport",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("application_id", models.CharField(max_length=5, null=True, verbose_name="ID заявки")),
                        ("description", models.TextField(blank=True, null=True)),
                        ("comment", models.TextField(verbose_name="комментарий")),
                        ("time", models.DateTimeField(verbose_name="время")),
                        ("user", models.CharField(max_length=40, verbose_name="пользователь")),
                    ],
                    options={"db_table": "history_application", "ordering": ["id"]},
                ),
            ],
        ),
        # Application создаётся отдельно — зависит от ApplicationStatus
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Application",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("last_update_date_time", models.DateTimeField(blank=True, null=True, verbose_name="Время последней активности")),
                        ("comment_monitoring", models.TextField(blank=True, max_length=300, null=True)),
                        ("time_monitoring", models.DateTimeField(blank=True, null=True)),
                        ("file_monitoring", models.FileField(blank=True, null=True, upload_to="application/")),
                        ("user_monitoring", models.CharField(blank=True, max_length=40, null=True)),
                        ("comment_control_apply", models.TextField(blank=True, max_length=300, null=True)),
                        ("time_control_apply", models.DateTimeField(blank=True, null=True)),
                        ("file_control_apply", models.FileField(blank=True, null=True, upload_to="files/")),
                        ("user_control_apply", models.CharField(blank=True, max_length=40, null=True)),
                        ("comment_control_send", models.TextField(blank=True, max_length=300, null=True)),
                        ("time_control_send", models.DateTimeField(blank=True, null=True)),
                        ("file_control_send", models.FileField(blank=True, null=True, upload_to="files/")),
                        ("user_control_send", models.CharField(blank=True, max_length=40, null=True)),
                        ("comment_service_apply", models.TextField(blank=True, max_length=300, null=True)),
                        ("time_service_apply", models.DateTimeField(blank=True, null=True)),
                        ("file_service_apply", models.FileField(blank=True, null=True, upload_to="files/")),
                        ("user_service_apply", models.CharField(blank=True, max_length=40, null=True)),
                        ("comment_control_at_work", models.TextField(blank=True, max_length=300, null=True)),
                        ("time_control_at_work", models.DateTimeField(blank=True, null=True)),
                        ("file_control_at_work", models.FileField(blank=True, null=True, upload_to="files/")),
                        ("user_control_at_work", models.CharField(blank=True, max_length=40, null=True)),
                        ("comment_control_unable", models.TextField(blank=True, max_length=300, null=True)),
                        ("time_control_unable", models.DateTimeField(blank=True, null=True)),
                        ("file_control_unable", models.FileField(blank=True, null=True, upload_to="files/")),
                        ("user_control_unable", models.CharField(blank=True, max_length=40, null=True)),
                        ("comment_control_archive", models.TextField(blank=True, max_length=300, null=True)),
                        ("time_control_archive", models.DateTimeField(blank=True, null=True)),
                        ("file_control_archive", models.FileField(blank=True, null=True, upload_to="files/")),
                        ("user_control_archive", models.CharField(blank=True, max_length=40, null=True)),
                        ("status", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="application", to="workflow_applications.applicationstatus", verbose_name="Статус")),
                    ],
                    options={"db_table": "application", "verbose_name": "Заявка", "ordering": ["id"]},
                ),
            ],
        ),
        # ApplicationEvent — НОВАЯ таблица
        migrations.CreateModel(
            name="ApplicationEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("stage", models.CharField(max_length=30, verbose_name="этап")),
                ("comment", models.TextField(blank=True, null=True, verbose_name="комментарий")),
                ("file", models.FileField(blank=True, null=True, upload_to="application/events/", verbose_name="файл")),
                ("actor_name", models.CharField(blank=True, max_length=80, verbose_name="имя исполнителя (snapshot)")),
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="время события")),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="application_events", to="user.msuser", verbose_name="исполнитель")),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="workflow_applications.application", verbose_name="заявка")),
            ],
            options={"db_table": "application_event", "verbose_name": "Событие заявки", "ordering": ["occurred_at"]},
        ),
    ]
