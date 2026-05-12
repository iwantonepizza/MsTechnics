from django.db import migrations


def validate_panel_fk_mappings(apps, schema_editor):
    checks = {
        "display": """
            SELECT id, display_id
            FROM public.panel
            WHERE display_id IS NOT NULL
              AND display_new_id IS NULL
            ORDER BY id
            LIMIT 10
        """,
        "condition": """
            SELECT id, condition_id
            FROM public.panel
            WHERE condition_id IS NOT NULL
              AND condition_new_id IS NULL
            ORDER BY id
            LIMIT 10
        """,
        "department": """
            SELECT id, department_id
            FROM public.panel
            WHERE department_id IS NOT NULL
              AND department_new_id IS NULL
            ORDER BY id
            LIMIT 10
        """,
    }

    with schema_editor.connection.cursor() as cursor:
        for label, sql in checks.items():
            cursor.execute(sql)
            rows = cursor.fetchall()
            if rows:
                raise RuntimeError(
                    f"Unmapped legacy panel.{label} values during id migration: {rows!r}"
                )


class Migration(migrations.Migration):
    dependencies = [
        ("directory_panels", "0003_alter_panel_options_alter_panel_condition_and_more"),
    ]
    atomic = False

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE public.panel
            ADD COLUMN display_new_id bigint NULL,
            ADD COLUMN condition_new_id bigint NULL,
            ADD COLUMN department_new_id bigint NULL;

            UPDATE public.panel AS p
            SET display_new_id = d.id
            FROM public.display AS d
            WHERE p.display_id = d.name;

            UPDATE public.panel AS p
            SET condition_new_id = c.id
            FROM public.condition AS c
            WHERE p.condition_id = c.name;

            UPDATE public.panel AS p
            SET department_new_id = d.id
            FROM public.department AS d
            WHERE p.department_id = d.name;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunPython(
            validate_panel_fk_mappings,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunSQL(
            sql="""
            ALTER TABLE public.panel
            DROP CONSTRAINT IF EXISTS panel_display_id_36368d17_fk_display_name,
            DROP CONSTRAINT IF EXISTS panel_condition_id_12b1a585_fk_condition_name,
            DROP CONSTRAINT IF EXISTS panel_department_id_d47663ed_fk_department_name;

            DROP INDEX IF EXISTS public.panel_display_id_36368d17_like;
            DROP INDEX IF EXISTS public.panel_display_id_36368d17;
            DROP INDEX IF EXISTS public.panel_condition_id_12b1a585_like;
            DROP INDEX IF EXISTS public.panel_condition_id_12b1a585;
            DROP INDEX IF EXISTS public.panel_department_id_d47663ed_like;
            DROP INDEX IF EXISTS public.panel_department_id_d47663ed;

            ALTER TABLE public.panel
            DROP COLUMN display_id,
            DROP COLUMN condition_id,
            DROP COLUMN department_id;

            ALTER TABLE public.panel
            RENAME COLUMN display_new_id TO display_id;

            ALTER TABLE public.panel
            RENAME COLUMN condition_new_id TO condition_id;

            ALTER TABLE public.panel
            RENAME COLUMN department_new_id TO department_id;

            CREATE INDEX panel_display_id_36368d17
            ON public.panel USING btree (display_id);

            CREATE INDEX panel_condition_id_12b1a585
            ON public.panel USING btree (condition_id);

            CREATE INDEX panel_department_id_d47663ed
            ON public.panel USING btree (department_id);

            ALTER TABLE public.panel
            ADD CONSTRAINT panel_display_id_36368d17_fk_display_id
            FOREIGN KEY (display_id)
            REFERENCES public.display(id)
            DEFERRABLE INITIALLY DEFERRED;

            ALTER TABLE public.panel
            ADD CONSTRAINT panel_condition_id_12b1a585_fk_condition_id
            FOREIGN KEY (condition_id)
            REFERENCES public.condition(id)
            DEFERRABLE INITIALLY DEFERRED;

            ALTER TABLE public.panel
            ADD CONSTRAINT panel_department_id_d47663ed_fk_department_id
            FOREIGN KEY (department_id)
            REFERENCES public.department(id)
            DEFERRABLE INITIALLY DEFERRED;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
