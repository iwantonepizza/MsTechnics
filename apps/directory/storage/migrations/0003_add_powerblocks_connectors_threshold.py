# Generated manually for T-7-005.
import apps.directory.storage.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("directory_storage", "0002_alter_hubs_options_alter_lamels_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="wires",
            name="low_stock_threshold",
            field=models.PositiveIntegerField(default=3, verbose_name="Порог низкого остатка"),
        ),
        migrations.AddField(
            model_name="hubs",
            name="low_stock_threshold",
            field=models.PositiveIntegerField(default=3, verbose_name="Порог низкого остатка"),
        ),
        migrations.AddField(
            model_name="lamels",
            name="low_stock_threshold",
            field=models.PositiveIntegerField(default=3, verbose_name="Порог низкого остатка"),
        ),
        migrations.CreateModel(
            name="PowerBlocks",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=20, unique=True, verbose_name="Имя")),
                (
                    "description",
                    models.CharField(
                        blank=True, max_length=100, null=True, verbose_name="Описание"
                    ),
                ),
                (
                    "count",
                    models.PositiveIntegerField(
                        default=0,
                        validators=[apps.directory.storage.models.validate_non_negative],
                        verbose_name="Количество",
                    ),
                ),
                (
                    "low_stock_threshold",
                    models.PositiveIntegerField(default=3, verbose_name="Порог низкого остатка"),
                ),
                (
                    "photo",
                    models.ImageField(
                        blank=True, null=True, upload_to="photos/", verbose_name="Фото"
                    ),
                ),
            ],
            options={
                "verbose_name": "Блок питания",
                "verbose_name_plural": "Блоки питания",
                "db_table": "power_blocks_zip",
                "ordering": ["id"],
            },
        ),
        migrations.CreateModel(
            name="Connectors",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=20, unique=True, verbose_name="Имя")),
                (
                    "description",
                    models.CharField(
                        blank=True, max_length=100, null=True, verbose_name="Описание"
                    ),
                ),
                (
                    "count",
                    models.PositiveIntegerField(
                        default=0,
                        validators=[apps.directory.storage.models.validate_non_negative],
                        verbose_name="Количество",
                    ),
                ),
                (
                    "low_stock_threshold",
                    models.PositiveIntegerField(default=3, verbose_name="Порог низкого остатка"),
                ),
                (
                    "photo",
                    models.ImageField(
                        blank=True, null=True, upload_to="photos/", verbose_name="Фото"
                    ),
                ),
            ],
            options={
                "verbose_name": "Коннектор",
                "verbose_name_plural": "Коннекторы",
                "db_table": "connectors_zip",
                "ordering": ["id"],
            },
        ),
    ]
