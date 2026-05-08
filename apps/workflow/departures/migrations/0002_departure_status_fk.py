"""
T-2-030: создаём DepartureStatus справочник + добавляем FK в Departure.
Data-миграция seeding и backfill здесь же.
"""
from django.db import migrations, models
import django.db.models.deletion


def seed_statuses(apps, schema_editor):
    DepartureStatus = apps.get_model("workflow_departures", "DepartureStatus")
    rows = [
        ("created",   "Создан",   0, False),
        ("completed", "Выполнен", 1, False),
        ("archived",  "В архиве", 2, True),
        ("deleted",   "Удалён",   3, True),
    ]
    for name, desc, order, terminal in rows:
        DepartureStatus.objects.get_or_create(
            name=name,
            defaults={"description": desc, "order": order, "is_terminal": terminal},
        )


def backfill_status_fk(apps, schema_editor):
    Departure = apps.get_model("workflow_departures", "Departure")
    DepartureStatus = apps.get_model("workflow_departures", "DepartureStatus")

    mapping = {
        "Создан":   "created",
        "Выполнен": "completed",
        "В архиве": "archived",
        "Удален":   "deleted",
        "Удалён":   "deleted",
    }
    name_to_id = dict(DepartureStatus.objects.values_list("name", "id"))
    unmapped = []

    for dep in Departure.objects.filter(status_id__isnull=True).iterator(chunk_size=500):
        legacy = dep.status_legacy or ""
        target = mapping.get(legacy.strip())
        if not target:
            unmapped.append((dep.id, legacy))
            # Ставим created по умолчанию чтобы не было NULL
            dep.status_id = name_to_id.get("created")
        else:
            dep.status_id = name_to_id[target]
        dep.save(update_fields=["status_id"])

    if unmapped:
        import structlog
        structlog.get_logger(__name__).warning(
            "departure_status_unmapped_values",
            count=len(unmapped),
            sample=unmapped[:10],
        )


class Migration(migrations.Migration):
    dependencies = [
        ("workflow_departures", "0001_initial_state_import"),
        ("core_references", "0001_initial_state_import"),
    ]

    operations = [
        # 1. Создаём справочник
        migrations.CreateModel(
            name="DepartureStatus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=40, unique=True, verbose_name="код")),
                ("description", models.CharField(max_length=80, verbose_name="название для UI")),
                ("order", models.PositiveSmallIntegerField(default=0, verbose_name="порядок")),
                ("is_terminal", models.BooleanField(default=False, verbose_name="терминальный")),
                ("color", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="core_references.color", verbose_name="цвет")),
                ("icon", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="core_references.smile", verbose_name="иконка")),
            ],
            options={"db_table": "departure_status", "ordering": ["order", "id"]},
        ),
        # 2. Seed справочника
        migrations.RunPython(seed_statuses, migrations.RunPython.noop),
        # 3. Добавляем nullable FK
        migrations.AddField(
            model_name="departure",
            name="status",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="departures",
                to="workflow_departures.departurestatus",
                verbose_name="Статус",
            ),
        ),
        # 4. Backfill
        migrations.RunPython(backfill_status_fk, migrations.RunPython.noop),
    ]
