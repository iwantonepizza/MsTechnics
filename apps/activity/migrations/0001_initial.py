"""T-2-022: Новая таблица activity_log."""
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("user", "0001_initial_state_import"),
    ]

    operations = [
        migrations.CreateModel(
            name="ActivityLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("actor_name", models.CharField(blank=True, max_length=80, verbose_name="имя исполнителя (snapshot)")),
                ("target_id", models.PositiveIntegerField(blank=True, null=True, verbose_name="ID объекта")),
                ("event_type", models.CharField(max_length=40, verbose_name="тип события")),
                ("description", models.TextField(blank=True, verbose_name="описание")),
                ("comment", models.TextField(blank=True, verbose_name="комментарий")),
                ("payload", models.JSONField(blank=True, default=dict, verbose_name="доп. данные")),
                ("occurred_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now, verbose_name="время события")),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True, verbose_name="IP адрес")),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="activity_log", to="user.msuser", verbose_name="исполнитель")),
                ("target_type", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="contenttypes.contenttype", verbose_name="тип объекта")),
            ],
            options={
                "verbose_name": "Запись журнала",
                "verbose_name_plural": "Журнал событий",
                "db_table": "activity_log",
                "ordering": ["-occurred_at"],
            },
        ),
        migrations.AddIndex(
            model_name="activitylog",
            index=models.Index(fields=["target_type", "target_id"], name="activity_target_idx"),
        ),
        migrations.AddIndex(
            model_name="activitylog",
            index=models.Index(fields=["event_type"], name="activity_event_type_idx"),
        ),
        migrations.AddIndex(
            model_name="activitylog",
            index=models.Index(fields=["actor"], name="activity_actor_idx"),
        ),
    ]
