from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("directory_displays", "0001_initial_state_import"),
    ]

    operations = [
        migrations.AddField(
            model_name="display",
            name="vnnox_device_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Серийник VNNOX для маппинга email-алармов",
                max_length=64,
                verbose_name="VNNOX device id",
            ),
        ),
    ]
