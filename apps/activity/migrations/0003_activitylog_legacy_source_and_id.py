from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("activity", "0002_alter_activitylog_actor_name_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="activitylog",
            name="legacy_id",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Первичный ключ строки в legacy history-таблице.",
                null=True,
                verbose_name="legacy id",
            ),
        ),
        migrations.AddField(
            model_name="activitylog",
            name="legacy_source",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Источник строки при backfill из legacy history-таблиц.",
                max_length=32,
                verbose_name="legacy source",
            ),
        ),
        migrations.AddConstraint(
            model_name="activitylog",
            constraint=models.UniqueConstraint(
                fields=("legacy_source", "legacy_id"),
                name="activity_legacy_source_id_uniq",
            ),
        ),
    ]
