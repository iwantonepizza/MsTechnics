from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("user", "0002_alter_msuser_options_alter_msuser_allowed_city_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE public."user" '
                        "ADD COLUMN IF NOT EXISTS max_id varchar(50) NULL;"
                    ),
                    reverse_sql=(
                        'ALTER TABLE public."user" '
                        "DROP COLUMN IF EXISTS max_id;"
                    ),
                ),
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE public."user" '
                        "ALTER COLUMN telegram_id TYPE varchar(20);"
                    ),
                    reverse_sql=(
                        'ALTER TABLE public."user" '
                        "ALTER COLUMN telegram_id TYPE varchar(10);"
                    ),
                ),
            ],
            state_operations=[],
        ),
    ]
