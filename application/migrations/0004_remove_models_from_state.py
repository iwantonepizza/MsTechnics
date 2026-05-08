from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("application", "0003_initial"),
        ("workflow_applications", "0004_strip_application_prefix"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="Application"),
                migrations.DeleteModel(name="ApplicationHistoryReport"),
                migrations.DeleteModel(name="ApplicationStatus"),
            ],
        ),
    ]
