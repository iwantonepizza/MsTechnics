from django.db import migrations

INTEGER_TYPES = {"smallint", "integer", "bigint"}


def _get_column_type(cursor, table_name, column_name):
    cursor.execute(
        """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
          AND column_name = %s
        """,
        [table_name, column_name],
    )
    row = cursor.fetchone()
    return row[0] if row else None


def _drop_column_dependencies(cursor, table_name, column_name):
    cursor.execute(f"""
        DO $$
        DECLARE constraint_name text;
        BEGIN
            FOR constraint_name IN
                SELECT con.conname
                FROM pg_constraint AS con
                JOIN pg_class AS rel
                  ON rel.oid = con.conrelid
                JOIN pg_namespace AS nsp
                  ON nsp.oid = rel.relnamespace
                JOIN unnest(con.conkey) AS conkey(attnum)
                  ON TRUE
                JOIN pg_attribute AS attr
                  ON attr.attrelid = rel.oid
                 AND attr.attnum = conkey.attnum
                WHERE nsp.nspname = 'public'
                  AND rel.relname = '{table_name}'
                  AND attr.attname = '{column_name}'
            LOOP
                EXECUTE format(
                    'ALTER TABLE public.{table_name} DROP CONSTRAINT %I',
                    constraint_name
                );
            END LOOP;
        END $$;
        """)
    cursor.execute(f"""
        DO $$
        DECLARE index_name text;
        BEGIN
            FOR index_name IN
                SELECT DISTINCT idx.relname
                FROM pg_class AS tab
                JOIN pg_namespace AS nsp
                  ON nsp.oid = tab.relnamespace
                JOIN pg_index AS ind
                  ON ind.indrelid = tab.oid
                JOIN pg_class AS idx
                  ON idx.oid = ind.indexrelid
                JOIN unnest(ind.indkey) AS indkey(attnum)
                  ON TRUE
                JOIN pg_attribute AS attr
                  ON attr.attrelid = tab.oid
                 AND attr.attnum = indkey.attnum
                WHERE nsp.nspname = 'public'
                  AND tab.relname = '{table_name}'
                  AND attr.attname = '{column_name}'
                  AND NOT ind.indisprimary
            LOOP
                EXECUTE format('DROP INDEX IF EXISTS public.%I', index_name);
            END LOOP;
        END $$;
        """)


def _ensure_city_fk(cursor):
    cursor.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint AS con
                JOIN pg_class AS rel
                  ON rel.oid = con.conrelid
                JOIN pg_namespace AS nsp
                  ON nsp.oid = rel.relnamespace
                JOIN pg_class AS target
                  ON target.oid = con.confrelid
                JOIN pg_namespace AS target_nsp
                  ON target_nsp.oid = target.relnamespace
                JOIN unnest(con.conkey) AS conkey(attnum)
                  ON TRUE
                JOIN pg_attribute AS attr
                  ON attr.attrelid = rel.oid
                 AND attr.attnum = conkey.attnum
                WHERE con.contype = 'f'
                  AND nsp.nspname = 'public'
                  AND rel.relname = 'daily_task'
                  AND attr.attname = 'city_id'
                  AND target_nsp.nspname = 'public'
                  AND target.relname = 'city'
            ) THEN
                ALTER TABLE public.daily_task
                ADD CONSTRAINT daily_task_city_id_fk_city_id
                FOREIGN KEY (city_id)
                REFERENCES public.city(id)
                DEFERRABLE INITIALLY DEFERRED;
            END IF;
        END $$;
        """)


def forwards(_apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        column_type = _get_column_type(cursor, "daily_task", "city_id")
        pending_column_type = _get_column_type(cursor, "daily_task", "city_new_id")

        if column_type is None:
            if pending_column_type not in INTEGER_TYPES:
                raise RuntimeError(
                    "Neither public.daily_task.city_id nor a recoverable bigint "
                    "public.daily_task.city_new_id column was found"
                )
            cursor.execute("""
                ALTER TABLE public.daily_task
                RENAME COLUMN city_new_id TO city_id
                """)
            column_type = pending_column_type

        if column_type not in INTEGER_TYPES:
            cursor.execute("""
                ALTER TABLE public.daily_task
                ADD COLUMN IF NOT EXISTS city_new_id bigint NULL
                """)
            cursor.execute("""
                UPDATE public.daily_task AS task
                SET city_new_id = city.id
                FROM public.city AS city
                WHERE task.city_new_id IS NULL
                  AND (
                    task.city_id = city.name
                    OR task.city_id = city.id::text
                  )
                """)
            cursor.execute("""
                SELECT id, city_id
                FROM public.daily_task
                WHERE city_id IS NOT NULL
                  AND city_new_id IS NULL
                ORDER BY id
                LIMIT 10
                """)
            rows = cursor.fetchall()
            if rows:
                raise RuntimeError(
                    "Unmapped legacy daily_task.city_id values during id migration: " f"{rows!r}"
                )

            _drop_column_dependencies(cursor, "daily_task", "city_id")
            cursor.execute("ALTER TABLE public.daily_task DROP COLUMN city_id")
            cursor.execute("""
                ALTER TABLE public.daily_task
                RENAME COLUMN city_new_id TO city_id
                """)

        cursor.execute("""
            SELECT task.id, task.city_id
            FROM public.daily_task AS task
            LEFT JOIN public.city AS city
              ON city.id = task.city_id
            WHERE task.city_id IS NULL
               OR city.id IS NULL
            ORDER BY task.id
            LIMIT 10
            """)
        rows = cursor.fetchall()
        if rows:
            raise RuntimeError("Invalid daily_task.city_id values after id migration: " f"{rows!r}")

        cursor.execute("""
            ALTER TABLE public.daily_task
            ALTER COLUMN city_id SET NOT NULL
            """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS daily_task_city_id_idx
            ON public.daily_task USING btree (city_id)
            """)
        _ensure_city_fk(cursor)


class Migration(migrations.Migration):
    dependencies = [
        ("core_references", "0003_convert_condition_department_style_fks_to_id"),
        ("workflow_daily_tasks", "0003_add_notified_stages_state"),
        ("zip", "0003_remove_models_from_state"),
    ]
    atomic = False

    operations = [
        migrations.RunPython(forwards, reverse_code=migrations.RunPython.noop),
    ]
