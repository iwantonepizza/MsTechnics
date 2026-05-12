from django.db import migrations


def validate_display_city_mapping(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, city_id
            FROM public.display
            WHERE city_id IS NOT NULL
              AND city_new_id IS NULL
            ORDER BY id
            LIMIT 10
            """
        )
        rows = cursor.fetchall()

    if rows:
        raise RuntimeError(
            "Unmapped legacy display.city values during id migration: "
            f"{rows!r}"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("directory_displays", "0004_alter_cell_options_alter_display_options_and_more"),
    ]
    atomic = False

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE public.display
            ADD COLUMN city_new_id bigint NULL;

            UPDATE public.display AS d
            SET city_new_id = c.id
            FROM public.city AS c
            WHERE d.city_id = c.name;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunPython(
            validate_display_city_mapping,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunSQL(
            sql="""
            ALTER TABLE public.display
            DROP CONSTRAINT IF EXISTS display_city_id_21080318_fk_city_name;

            DROP INDEX IF EXISTS public.display_city_id_21080318_like;
            DROP INDEX IF EXISTS public.display_city_id_21080318;

            ALTER TABLE public.display
            DROP COLUMN city_id;

            ALTER TABLE public.display
            RENAME COLUMN city_new_id TO city_id;

            ALTER TABLE public.display
            ALTER COLUMN city_id SET NOT NULL;

            CREATE INDEX display_city_id_21080318
            ON public.display USING btree (city_id);

            ALTER TABLE public.display
            ADD CONSTRAINT display_city_id_21080318_fk_city_id
            FOREIGN KEY (city_id)
            REFERENCES public.city(id)
            DEFERRABLE INITIALLY DEFERRED;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
