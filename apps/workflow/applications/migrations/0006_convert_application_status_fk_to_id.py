from django.db import migrations


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
    if not row:
        raise RuntimeError(f"public.{table_name}.{column_name} column not found")
    return row[0]


def _drop_column_dependencies(cursor, table_name, column_name):
    cursor.execute(
        f"""
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
        """
    )
    cursor.execute(
        f"""
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
        """
    )


def _ensure_fk(cursor, table_name, column_name, target_table):
    constraint_name = f"{table_name}_{column_name}_fk_{target_table}_id"
    cursor.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint AS con
                JOIN pg_class AS rel
                  ON rel.oid = con.conrelid
                JOIN pg_namespace AS nsp
                  ON nsp.oid = rel.relnamespace
                WHERE nsp.nspname = 'public'
                  AND rel.relname = '{table_name}'
                  AND con.conname = '{constraint_name}'
            ) THEN
                ALTER TABLE public.{table_name}
                ADD CONSTRAINT {constraint_name}
                FOREIGN KEY ({column_name})
                REFERENCES public.{target_table}(id)
                DEFERRABLE INITIALLY DEFERRED;
            END IF;
        END $$;
        """
    )


def _convert_fk(
    cursor,
    *,
    table_name,
    column_name,
    target_table,
    target_lookup_column,
    nullable,
):
    column_type = _get_column_type(cursor, table_name, column_name)
    temp_column = f"{column_name[:-3]}_new_id"

    if column_type not in {"smallint", "integer", "bigint"}:
        cursor.execute(
            f"""
            ALTER TABLE public.{table_name}
            ADD COLUMN IF NOT EXISTS {temp_column} bigint NULL
            """
        )
        cursor.execute(
            f"""
            UPDATE public.{table_name} AS src
            SET {temp_column} = dst.id
            FROM public.{target_table} AS dst
            WHERE src.{column_name} = dst.{target_lookup_column}
              AND src.{temp_column} IS NULL
            """
        )
        cursor.execute(
            f"""
            SELECT id, {column_name}
            FROM public.{table_name}
            WHERE {column_name} IS NOT NULL
              AND {temp_column} IS NULL
            ORDER BY id
            LIMIT 10
            """
        )
        rows = cursor.fetchall()
        if rows:
            raise RuntimeError(
                f"Unmapped legacy {table_name}.{column_name} values during id migration: "
                f"{rows!r}"
            )

        _drop_column_dependencies(cursor, table_name, column_name)
        cursor.execute(f"ALTER TABLE public.{table_name} DROP COLUMN {column_name}")
        cursor.execute(
            f"""
            ALTER TABLE public.{table_name}
            RENAME COLUMN {temp_column} TO {column_name}
            """
        )

    if not nullable:
        cursor.execute(
            f"""
            SELECT id
            FROM public.{table_name}
            WHERE {column_name} IS NULL
            ORDER BY id
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if row:
            raise RuntimeError(
                f"{table_name}.{column_name} contains NULL after legacy FK conversion: "
                f"{row[0]!r}"
            )
        cursor.execute(
            f"""
            ALTER TABLE public.{table_name}
            ALTER COLUMN {column_name} SET NOT NULL
            """
        )

    cursor.execute(
        f"""
        CREATE INDEX IF NOT EXISTS {table_name}_{column_name}_idx
        ON public.{table_name} USING btree ({column_name})
        """
    )
    _ensure_fk(cursor, table_name, column_name, target_table)


def forwards(_apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        _convert_fk(
            cursor,
            table_name="application",
            column_name="status_id",
            target_table="application_status",
            target_lookup_column="name",
            nullable=False,
        )
        _convert_fk(
            cursor,
            table_name="application_status",
            column_name="color_id",
            target_table="color",
            target_lookup_column="name",
            nullable=False,
        )
        _convert_fk(
            cursor,
            table_name="application_status",
            column_name="color_text_id",
            target_table="color",
            target_lookup_column="name",
            nullable=False,
        )
        _convert_fk(
            cursor,
            table_name="application_status",
            column_name="icon_id",
            target_table="smile",
            target_lookup_column="smile_icon",
            nullable=True,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("workflow_applications", "0005_alter_application_options_and_more"),
    ]
    atomic = False

    operations = [
        migrations.RunPython(forwards, reverse_code=migrations.RunPython.noop),
    ]
