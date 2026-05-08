"""T-2-025 Wave 1: Application.panel FK name→id."""
from django.db import migrations, models
import django.db.models.deletion


def backfill_panel(apps, schema_editor):
    Application = apps.get_model("workflow_applications", "Application")
    Panel = apps.get_model("directory_panels", "Panel")
    name_to_id = dict(Panel.objects.values_list("name", "id"))
    for app in Application.objects.filter(panel_new_id__isnull=True).iterator(chunk_size=500):
        new_id = name_to_id.get(app.panel_id)
        if new_id:
            app.panel_new_id = new_id
            app.save(update_fields=["panel_new_id"])


class Migration(migrations.Migration):
    dependencies = [
        ("workflow_applications", "0002_display_fk_to_id"),
        ("directory_panels", "0001_initial_state_import"),
    ]
    atomic = False

    operations = [
        migrations.AddField(
            model_name="application",
            name="panel_new_id",
            field=models.IntegerField(null=True, blank=True, db_index=True),
        ),
        migrations.RunPython(backfill_panel, migrations.RunPython.noop),
        migrations.RemoveField(model_name="application", name="panel"),
        migrations.RenameField(
            model_name="application", old_name="panel_new_id", new_name="panel_id"
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="application",
                    name="panel",
                    field=models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="applications",
                        to="directory_panels.panel",
                        verbose_name="панель",
                    ),
                ),
            ],
        ),
    ]
