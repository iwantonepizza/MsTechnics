from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(db_index=True, max_length=64, unique=True)),
                ("description", models.CharField(blank=True, max_length=200)),
                ("text", models.TextField(help_text="Text with {placeholders} rendered from context")),
            ],
            options={
                "db_table": "notification_template",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rendered_text", models.TextField(blank=True)),
                ("context", models.JSONField(blank=True, default=dict)),
                ("related_target_id", models.CharField(blank=True, max_length=64, null=True)),
                ("status", models.CharField(choices=[("pending", "В очереди"), ("sent", "Отправлено"), ("failed", "Ошибка"), ("skipped", "Пропущено")], db_index=True, default="pending", max_length=16)),
                ("primary_channel", models.CharField(blank=True, max_length=16)),
                ("delivered_via", models.CharField(blank=True, max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to=settings.AUTH_USER_MODEL)),
                ("related_target_ct", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="contenttypes.contenttype")),
                ("template", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="notifications.notificationtemplate")),
            ],
            options={
                "db_table": "notification",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="NotificationDeliveryAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("channel", models.CharField(max_length=16)),
                ("attempted_at", models.DateTimeField(auto_now_add=True)),
                ("succeeded", models.BooleanField()),
                ("error_message", models.TextField(blank=True)),
                ("response_payload", models.JSONField(blank=True, default=dict)),
                ("notification", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attempts", to="notifications.notification")),
            ],
            options={
                "db_table": "notification_delivery_attempt",
                "ordering": ["attempted_at", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["recipient", "status", "-created_at"], name="notificatio_recipie_f683ec_idx"),
        ),
    ]
