"""apps/directory/panels/managers.py — менеджер панелей с аннотацией application_status."""

from django.db import models


class PanelQuerySet(models.QuerySet):
    def with_application_status(self):
        """
        Аннотирует queryset полем `_active_application_status_name`.
        Используй в views вместо обращения к panel.application_status (N+1).

        Пример:
            panels = Panel.objects.with_application_status().select_related(
                'condition', 'department'
            )
            # В шаблоне: panel._active_application_status_name|default:'default'
        """
        from django.db.models import OuterRef, Subquery

        # Импорт здесь — избегаем circular import
        application_model = apps_get_application()

        active_status_subquery = (
            application_model.objects.filter(panel=OuterRef("pk"))
            .exclude(status__name__in=["archive_done", "archive_unable"])
            .order_by("-last_update_date_time", "-id")
            .values("status__name")[:1]
        )

        return self.annotate(_active_application_status_name=Subquery(active_status_subquery))


def apps_get_application():
    """Lazy import чтобы избежать circular import между directory и workflow."""
    from django.apps import apps

    return apps.get_model("workflow_applications", "Application")


class PanelManager(models.Manager.from_queryset(PanelQuerySet)):
    pass
