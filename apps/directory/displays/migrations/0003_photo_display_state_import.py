from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("directory_displays", "0002_display_vnnox_device_id"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="PhotoDisplay",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("image", models.ImageField(upload_to="photos/display_photos/", verbose_name="Фото")),
                        ("uploaded_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")),
                        ("display", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="photos", to="directory_displays.display", verbose_name="Экран")),
                    ],
                    options={"db_table": "photo_display", "verbose_name": "Фото экрана", "verbose_name_plural": "Фото экрана", "ordering": ["id"]},
                ),
            ],
        ),
    ]
