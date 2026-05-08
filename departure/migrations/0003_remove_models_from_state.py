from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("departure", "0002_initial"),
        ("workflow_departures", "0003_contact_state_import"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="Contact"),
                migrations.DeleteModel(name="DepartureHistoryReport"),
                migrations.DeleteModel(name="Departure"),
                migrations.DeleteModel(name="Executor"),
            ],
        ),
    ]
