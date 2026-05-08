"""
apps/shared_migrations/utils.py — утилиты для data-миграций FK name→id.
T-2-025: вспомогательные функции backfill.
"""
import structlog

logger = structlog.get_logger(__name__)


def backfill_fk_name_to_id(
    *,
    qs,
    source_field: str,
    target_field: str,
    lookup_model,
    lookup_field: str = "name",
    chunk_size: int = 500,
) -> tuple[int, list]:
    """
    Заполняет target_field из source_field через lookup_model.name → id.
    Возвращает (updated_count, unmapped_pks_with_values).
    """
    name_to_id = dict(lookup_model.objects.values_list(lookup_field, "id"))
    updated, unmapped = 0, []

    for obj in qs.iterator(chunk_size=chunk_size):
        source_val = getattr(obj, source_field)
        new_id = name_to_id.get(source_val)
        if new_id is None:
            unmapped.append((obj.pk, source_val))
        else:
            setattr(obj, target_field, new_id)
            obj.save(update_fields=[target_field])
            updated += 1

    if unmapped:
        logger.warning("fk_backfill_unmapped", field=source_field,
                       count=len(unmapped), sample=unmapped[:5])

    return updated, unmapped
