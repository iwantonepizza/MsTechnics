from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from django.apps import apps
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction


@dataclass(frozen=True)
class MediaReference:
    app_label: str
    model_name: str
    field_name: str
    delete_record: bool = False


MEDIA_REFERENCES = (
    MediaReference("directory_displays", "Display", "file"),
    MediaReference("directory_displays", "Display", "project_photo"),
    MediaReference("directory_displays", "PhotoDisplay", "image", delete_record=True),
    MediaReference("directory_storage", "Wires", "photo"),
    MediaReference("directory_storage", "Hubs", "photo"),
    MediaReference("directory_storage", "Lamels", "photo"),
    MediaReference("directory_storage", "PowerBlocks", "photo"),
    MediaReference("directory_storage", "Connectors", "photo"),
)

PLACEHOLDER_STEMS = {
    "probka",
    "photo_not_found",
    "file_not_found",
}


def is_placeholder_name(name: str) -> bool:
    stem = PurePosixPath(name).stem.casefold()
    return any(
        stem == candidate or stem.startswith(f"{candidate}_") for candidate in PLACEHOLDER_STEMS
    )


class Command(BaseCommand):
    help = "Audit media references; optionally clear missing references and obvious placeholders."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--apply", action="store_true", help="Apply changes. Default is dry-run."
        )
        parser.add_argument(
            "--delete-placeholders",
            action="store_true",
            help="Also clear and physically delete probka/photo_not_found/file_not_found files.",
        )

    def handle(self, *_args, **options) -> None:
        apply_changes = options["apply"]
        delete_placeholders = options["delete_placeholders"]
        counters = {"missing": 0, "placeholder_refs": 0, "cleared": 0, "deleted_files": 0}
        placeholder_files: set[str] = set()

        with transaction.atomic():
            for spec in MEDIA_REFERENCES:
                model = apps.get_model(spec.app_label, spec.model_name)
                queryset = model._default_manager.exclude(**{spec.field_name: ""}).exclude(
                    **{spec.field_name: None}
                )
                for obj in queryset.iterator():
                    field_file = getattr(obj, spec.field_name)
                    name = getattr(field_file, "name", "") or ""
                    missing = not default_storage.exists(name)
                    placeholder = is_placeholder_name(name)
                    if missing:
                        counters["missing"] += 1
                    if placeholder:
                        counters["placeholder_refs"] += 1
                        placeholder_files.add(name)
                    if not missing and not (delete_placeholders and placeholder):
                        continue

                    reason = "missing" if missing else "placeholder"
                    self.stdout.write(
                        f"{spec.model_name}#{obj.pk}.{spec.field_name}: {name} [{reason}]"
                    )
                    if not apply_changes:
                        continue
                    if spec.delete_record:
                        obj.delete()
                    else:
                        setattr(obj, spec.field_name, None)
                        obj.save(update_fields=[spec.field_name])
                    counters["cleared"] += 1

            if delete_placeholders:
                placeholder_files.update(self._find_placeholder_files())
                for name in sorted(placeholder_files):
                    self.stdout.write(f"storage placeholder: {name}")
                    if apply_changes and default_storage.exists(name):
                        default_storage.delete(name)
                        counters["deleted_files"] += 1

            if not apply_changes:
                transaction.set_rollback(True)

        mode = "APPLIED" if apply_changes else "DRY RUN"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode}: missing={counters['missing']} "
                f"placeholder_refs={counters['placeholder_refs']} "
                f"cleared={counters['cleared']} deleted_files={counters['deleted_files']}"
            )
        )

    def _find_placeholder_files(self, directory: str = "") -> set[str]:
        found: set[str] = set()
        directories, files = default_storage.listdir(directory)
        for file_name in files:
            path = f"{directory}/{file_name}".lstrip("/")
            if is_placeholder_name(path):
                found.add(path)
        for child in directories:
            path = f"{directory}/{child}".lstrip("/")
            found.update(self._find_placeholder_files(path))
        return found
