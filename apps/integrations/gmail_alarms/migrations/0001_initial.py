from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("directory_displays", "0002_display_vnnox_device_id"),
        ("directory_panels", "0002_remove_panel_application_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="AlarmEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("type", models.CharField(choices=[("faulty", "Аварийное"), ("recovery", "Восстановление")], db_index=True, max_length=10)),
                ("device_id", models.CharField(db_index=True, max_length=64)),
                ("screen_name_raw", models.CharField(max_length=200)),
                ("receiving_card_no", models.PositiveIntegerField()),
                ("raw_position", models.CharField(blank=True, max_length=300)),
                ("raw_email_subject", models.CharField(blank=True, max_length=300)),
                ("gmail_message_id", models.CharField(blank=True, db_index=True, max_length=100)),
                ("occurred_at", models.DateTimeField(db_index=True)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("resolved_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("cell", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="directory_displays.cell")),
                ("display", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="vnnox_alarms", to="directory_displays.display")),
                ("panel", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="directory_panels.panel")),
                ("resolved_by_alarm", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="resolves", to="gmail_alarms.alarmevent")),
            ],
            options={
                "db_table": "alarm_event",
                "ordering": ["-occurred_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="alarmevent",
            index=models.Index(fields=["device_id", "receiving_card_no", "-occurred_at"], name="alarm_event_device__7a3d9f_idx"),
        ),
        migrations.AddIndex(
            model_name="alarmevent",
            index=models.Index(fields=["display", "resolved_at", "-occurred_at"], name="alarm_event_display_11e9ef_idx"),
        ),
        migrations.AddConstraint(
            model_name="alarmevent",
            constraint=models.UniqueConstraint(fields=("gmail_message_id", "type", "device_id", "receiving_card_no", "occurred_at"), name="unique_vnnox_alarm_from_email"),
        ),
    ]
