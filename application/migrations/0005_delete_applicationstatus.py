from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("application", "0004_remove_models_from_state"),
        ("zip", "0003_remove_models_from_state"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="ApplicationStatus"),
            ],
        ),
    ]
