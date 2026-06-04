from django.db import migrations


def validate_daily_task_city_mapping(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'daily_task'
              AND column_name = 'city_id'
            """
        )
        row = cursor.fetchone()
        if not row or row[0] == "bigint":
            return

        cursor.execute(
            """
            SELECT dt.id, dt.city_id
            FROM daily_task dt
            LEFT JOIN city c
              ON dt.city_id = c.name OR dt.city_id = c.id::text
            WHERE c.id IS NULL
            ORDER BY dt.id
            """
        )
        unmatched = cursor.fetchall()
        if unmatched:
            preview = ", ".join(f"id={task_id} city_id={city_id!r}" for task_id, city_id in unmatched[:10])
            raise RuntimeError(f"Cannot convert daily_task.city_id to city.id; unmatched rows: {preview}")


class Migration(migrations.Migration):
    dependencies = [
        ("workflow_daily_tasks", "0003_add_notified_stages_state"),
    ]

    operations = [
        migrations.RunPython(
            validate_daily_task_city_mapping,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1
                            FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND table_name = 'daily_task'
                              AND column_name = 'city_id'
                              AND data_type <> 'bigint'
                        ) THEN
                            ALTER TABLE daily_task ADD COLUMN city_id_new bigint;

                            UPDATE daily_task dt
                            SET city_id_new = c.id
                            FROM city c
                            WHERE dt.city_id = c.name OR dt.city_id = c.id::text;

                            IF EXISTS (SELECT 1 FROM daily_task WHERE city_id_new IS NULL) THEN
                                RAISE EXCEPTION 'Cannot convert daily_task.city_id: unresolved city rows remain';
                            END IF;

                            ALTER TABLE daily_task DROP COLUMN city_id;
                            ALTER TABLE daily_task RENAME COLUMN city_id_new TO city_id;
                            ALTER TABLE daily_task ALTER COLUMN city_id SET NOT NULL;
                        END IF;

                        IF NOT EXISTS (
                            SELECT 1
                            FROM pg_constraint
                            WHERE conname = 'daily_task_city_id_fk'
                        ) THEN
                            ALTER TABLE daily_task
                            ADD CONSTRAINT daily_task_city_id_fk
                            FOREIGN KEY (city_id)
                            REFERENCES city(id)
                            DEFERRABLE INITIALLY DEFERRED;
                        END IF;
                    END $$;

                    CREATE INDEX IF NOT EXISTS daily_task_city_id_idx
                    ON daily_task(city_id);
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                )
            ],
            state_operations=[],
        ),
    ]
