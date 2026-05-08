"""apps/workflow/applications/managers.py — менеджер заявок."""
from django.db import models

ARCHIVE_STATUSES = ("archive_done", "archive_unable")


class ApplicationManager(models.Manager):
    """
    .all_new() — активные заявки без архива (для дашбордов).
    .all()     — все заявки (для архивной вкладки, admin, отчётов).
    """

    def all_new(self):
        return self.exclude(status__name__in=ARCHIVE_STATUSES)
