"""T-2-013: импорт таблиц wires_zip, hubs_zip, lamels_storage."""
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Wires",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("name", models.CharField(max_length=20, unique=True)),
                        ("description", models.CharField(blank=True, max_length=100, null=True)),
                        ("count", models.PositiveIntegerField(default=0)),
                        ("photo", models.ImageField(blank=True, null=True, upload_to="photos/")),
                    ],
                    options={"db_table": "wires_zip"},
                ),
                migrations.CreateModel(
                    name="Hubs",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("name", models.CharField(max_length=20, unique=True)),
                        ("description", models.CharField(blank=True, max_length=100, null=True)),
                        ("count", models.PositiveIntegerField(default=0)),
                        ("photo", models.ImageField(blank=True, null=True, upload_to="photos/")),
                    ],
                    options={"db_table": "hubs_zip"},
                ),
                migrations.CreateModel(
                    name="Lamels",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                        ("name", models.CharField(max_length=20, unique=True)),
                        ("description", models.CharField(blank=True, max_length=100, null=True)),
                        ("count", models.PositiveIntegerField(default=0)),
                        ("photo", models.ImageField(blank=True, null=True, upload_to="photos/")),
                    ],
                    options={"db_table": "lamels_storage"},
                ),
            ],
        ),
    ]
