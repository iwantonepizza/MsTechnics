from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0002_remove_models_from_state"),
        ("application", "0005_delete_applicationstatus"),
        ("user", "0002_alter_msuser_options_alter_msuser_allowed_city_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="Cities"),
                migrations.RemoveField(model_name="condition", name="color"),
                migrations.RemoveField(model_name="condition", name="color_text"),
                migrations.RemoveField(model_name="condition", name="icon"),
                migrations.RemoveField(model_name="department", name="color"),
                migrations.RemoveField(model_name="department", name="color_text"),
                migrations.RemoveField(model_name="department", name="icon"),
                migrations.DeleteModel(name="Color"),
                migrations.DeleteModel(name="Condition"),
                migrations.DeleteModel(name="Department"),
                migrations.DeleteModel(name="Smile"),
            ],
        ),
    ]
