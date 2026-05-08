"""
T-2-012: импортируем существующие таблицы в state нового app.
SeparateDatabaseAndState — database_operations пустые (таблицы уже есть в БД),
state_operations — CreateModel (Django узнаёт о моделях).
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],   # таблицы уже существуют — ничего не создаём
            state_operations=[
                migrations.CreateModel(
                    name="Color",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("name", models.CharField(max_length=15, unique=True, verbose_name="Цвет")),
                        ("hex_color", models.CharField(max_length=7, unique=True, verbose_name="Код цвета")),
                    ],
                    options={"db_table": "color", "verbose_name": "Цвет", "ordering": ["id"]},
                ),
                migrations.CreateModel(
                    name="Smile",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("smile_icon", models.CharField(max_length=15, unique=True, verbose_name="Иконка")),
                    ],
                    options={"db_table": "smile", "verbose_name": "Иконка", "ordering": ["id"]},
                ),
                migrations.CreateModel(
                    name="Cities",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("name", models.CharField(max_length=15, unique=True, verbose_name="имя")),
                        ("slug", models.SlugField(blank=True, null=True, unique=True, verbose_name="URL")),
                        ("description", models.TextField(blank=True, null=True, verbose_name="описание")),
                    ],
                    options={"db_table": "city", "verbose_name": "Город", "ordering": ["id"]},
                ),
                migrations.CreateModel(
                    name="Condition",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("name", models.CharField(max_length=15, unique=True, verbose_name="Состояние")),
                        ("description", models.TextField(blank=True, null=True, verbose_name="описание")),
                        ("color", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="condition_color", to="core_references.color", verbose_name="цвет фона")),
                        ("color_text", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="condition_color_text", to="core_references.color", verbose_name="цвет текста")),
                        ("icon", models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to="core_references.smile", verbose_name="иконка")),
                    ],
                    options={"db_table": "condition", "verbose_name": "Состояние", "ordering": ["id"]},
                ),
                migrations.CreateModel(
                    name="Department",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("name", models.CharField(max_length=20, unique=True, verbose_name="название отдела")),
                        ("description", models.TextField(blank=True, null=True, verbose_name="описание")),
                        ("color", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="department_color", to="core_references.color", verbose_name="цвет")),
                        ("color_text", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="department_color_text", to="core_references.color", verbose_name="цвет текста")),
                        ("icon", models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to="core_references.smile", verbose_name="иконка")),
                    ],
                    options={"db_table": "department", "verbose_name": "Отдел", "ordering": ["id"]},
                ),
            ],
        ),
    ]
