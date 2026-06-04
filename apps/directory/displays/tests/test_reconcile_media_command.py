from io import StringIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from apps.directory.displays.models import PhotoDisplay
from tests.factories import DisplayFactory

pytestmark = pytest.mark.django_db


def test_placeholder_name_detection_is_conservative() -> None:
    from apps.directory.displays.management.commands.reconcile_media import is_placeholder_name

    assert is_placeholder_name("files/probka.jpg")
    assert is_placeholder_name("files/photo_not_found_XYZ.png")
    assert not is_placeholder_name("files/plan_malkova.jpg")
    assert not is_placeholder_name("photos/logo_black.png")


def test_reconcile_media_dry_run_and_apply(tmp_path, settings) -> None:
    settings.MEDIA_ROOT = tmp_path
    display = DisplayFactory(
        name="media-reconcile-display",
        file="files/missing.pdf",
        project_photo=SimpleUploadedFile(
            "project.pdf",
            b"%PDF-1.4 project",
            content_type="application/pdf",
        ),
    )
    placeholder = PhotoDisplay.objects.create(
        display=display,
        image=SimpleUploadedFile(
            "photo_not_found.png",
            b"placeholder",
            content_type="image/png",
        ),
    )

    dry_run = StringIO()
    call_command("reconcile_media", delete_placeholders=True, stdout=dry_run)

    display.refresh_from_db()
    assert display.file.name == "files/missing.pdf"
    assert PhotoDisplay.objects.filter(pk=placeholder.pk).exists()
    assert "DRY RUN" in dry_run.getvalue()

    applied = StringIO()
    call_command("reconcile_media", apply=True, delete_placeholders=True, stdout=applied)

    display.refresh_from_db()
    assert not display.file
    assert display.project_photo
    assert not PhotoDisplay.objects.filter(pk=placeholder.pk).exists()
    assert "APPLIED" in applied.getvalue()
