"""
T-2-025 Wave 1: Application.display FK name→id.

Три шага:
  1. display_new_id: добавляем nullable int
  2. backfill: display_name → display.id
  3. replace: удаляем старый, переименовываем, добавляем FK
"""
from django.db import migrations, models
import django.db.models.deletion


def backfill_display(apps, schema_editor):
    Application = apps.get_model("workflow_applications", "Application")
    Display = apps.get_model("directory_displays", "Display")
    name_to_id = dict(Display.objects.values_list("name", "id"))
    unmapped = []
    for app in Application.objects.filter(display_new_id__isnull=True).iterator(chunk_size=500):
        new_id = name_to_id.get(app.display_id)  # display_id хранит name (to_field='name')
        if new_id is None:
            unmapped.append((app.pk, app.display_id))
        else:
            app.display_new_id = new_id
            app.save(update_fields=["display_new_id"])
    if unmapped:
        import structlog
        structlog.get_logger(__name__).warning(
            "t2025_application_display_unmapped", sample=unmapped[:5]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("workflow_applications", "0001_extra_legacy_fk_state"),
        ("directory_displays", "0001_initial_state_import"),
    ]
    atomic = False  # backfill большой таблицы — без глобальной транзакции

    operations = [
        # Step 1: add new column
        migrations.AddField(
            model_name="application",
            name="display_new_id",
            field=models.IntegerField(null=True, blank=True, db_index=True),
        ),
        # Step 2: backfill
        migrations.RunPython(backfill_display, migrations.RunPython.noop),
        # Step 3: replace FK
        migrations.RemoveField(model_name="application", name="display"),
        migrations.RenameField(
            model_name="application",
            old_name="display_new_id",
            new_name="display_id",
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],  # display_id колонка уже есть
            state_operations=[
                migrations.AddField(
                    model_name="application",
                    name="display",
                    field=models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="applications",
                        to="directory_displays.display",
                        verbose_name="экран",
                    ),
                ),
            ],
        ),
    ]
