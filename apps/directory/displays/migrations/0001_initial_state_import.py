"""T-2-013: импортируем существующие таблицы display, cell."""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [("core_references", "0001_initial_state_import")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Display",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("name", models.CharField(max_length=20, unique=True, verbose_name="экран")),
                        ("description", models.TextField(blank=True, null=True)),
                        ("rows", models.PositiveIntegerField(default=0)),
                        ("cols", models.PositiveIntegerField(default=0)),
                        ("camera_link", models.URLField(max_length=150, null=True)),
                        ("file", models.FileField(blank=True, null=True, upload_to="files/")),
                        ("project_photo", models.FileField(blank=True, null=True, upload_to="files/")),
                        ("slug", models.SlugField(blank=True, null=True, unique=True)),
                        ("city", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="display", to="core_references.cities", to_field="name", verbose_name="город")),
                    ],
                    options={"db_table": "display", "verbose_name": "Экран", "ordering": ["id"]},
                ),
                migrations.CreateModel(
                    name="Cell",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("row", models.PositiveIntegerField(editable=False, verbose_name="ряд")),
                        ("col", models.PositiveIntegerField(editable=False, verbose_name="столбец")),
                        ("display", models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name="cell_set", to="directory_displays.display", to_field="name", verbose_name="экран")),
                        ("panel", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="cell", to="directory_panels.panel", to_field="name", verbose_name="панель")),
                    ],
                    options={"db_table": "cell", "verbose_name": "Ячейка", "ordering": ["display", "row", "col"]},
                ),
            ],
        ),
    ]
