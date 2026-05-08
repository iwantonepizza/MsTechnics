from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0001_initial"),
        ("core_references", "0001_initial_state_import"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="Condition"),
                migrations.DeleteModel(name="Department"),
                migrations.DeleteModel(name="Cities"),
                migrations.DeleteModel(name="Color"),
                migrations.DeleteModel(name="Smile"),
            ],
        ),
    ]
