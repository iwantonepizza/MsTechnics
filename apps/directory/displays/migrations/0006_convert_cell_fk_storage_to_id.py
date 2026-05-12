from django.db import migrations


def validate_cell_fk_mappings(apps, schema_editor):
    checks = {
        "display": """
            SELECT id, display_id
            FROM public.cell
            WHERE display_id IS NOT NULL
              AND display_new_id IS NULL
            ORDER BY id
            LIMIT 10
        """,
        "panel": """
            SELECT id, panel_id
            FROM public.cell
            WHERE panel_id IS NOT NULL
              AND panel_new_id IS NULL
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
                    f"Unmapped legacy cell.{label} values during id migration: {rows!r}"
                )


class Migration(migrations.Migration):
    dependencies = [
        ("directory_displays", "0005_convert_display_city_fk_to_id"),
        ("directory_panels", "0004_convert_panel_fk_storage_to_id"),
    ]
    atomic = False

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE public.cell
            ADD COLUMN display_new_id bigint NULL,
            ADD COLUMN panel_new_id bigint NULL;

            UPDATE public.cell AS c
            SET display_new_id = d.id
            FROM public.display AS d
            WHERE c.display_id = d.name;

            UPDATE public.cell AS c
            SET panel_new_id = p.id
            FROM public.panel AS p
            WHERE c.panel_id = p.name;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunPython(
            validate_cell_fk_mappings,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunSQL(
            sql="""
            ALTER TABLE public.cell
            DROP CONSTRAINT IF EXISTS cell_display_id_3314090f_fk_display_name,
            DROP CONSTRAINT IF EXISTS cell_panel_id_676cbe77_fk_panel_name,
            DROP CONSTRAINT IF EXISTS unique_display_row_col,
            DROP CONSTRAINT IF EXISTS unique_panel;

            DROP INDEX IF EXISTS public.cell_display_id_3314090f_like;
            DROP INDEX IF EXISTS public.cell_display_id_3314090f;
            DROP INDEX IF EXISTS public.cell_panel_id_676cbe77_like;
            DROP INDEX IF EXISTS public.cell_panel_id_676cbe77;

            ALTER TABLE public.cell
            DROP COLUMN display_id,
            DROP COLUMN panel_id;

            ALTER TABLE public.cell
            RENAME COLUMN display_new_id TO display_id;

            ALTER TABLE public.cell
            RENAME COLUMN panel_new_id TO panel_id;

            ALTER TABLE public.cell
            ALTER COLUMN display_id SET NOT NULL;

            CREATE INDEX cell_display_id_3314090f
            ON public.cell USING btree (display_id);

            CREATE INDEX cell_panel_id_676cbe77
            ON public.cell USING btree (panel_id);

            ALTER TABLE public.cell
            ADD CONSTRAINT cell_display_id_3314090f_fk_display_id
            FOREIGN KEY (display_id)
            REFERENCES public.display(id)
            DEFERRABLE INITIALLY DEFERRED;

            ALTER TABLE public.cell
            ADD CONSTRAINT cell_panel_id_676cbe77_fk_panel_id
            FOREIGN KEY (panel_id)
            REFERENCES public.panel(id)
            DEFERRABLE INITIALLY DEFERRED;

            ALTER TABLE public.cell
            ADD CONSTRAINT unique_panel UNIQUE (panel_id);

            ALTER TABLE public.cell
            ADD CONSTRAINT unique_display_row_col UNIQUE (display_id, "row", col);
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
