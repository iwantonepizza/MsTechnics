"""
apps/directory/panels/models.py — Panel (ex-Panels).

T-2-013: перенесено из zip/models.py, модель переименована Panels→Panel.
Panels = Panel — alias для обратной совместимости старых импортов.
db_table='panel' — оригинальное имя таблицы, данные сохранены.
"""
from django.db import models

import structlog

from apps.directory.panels.managers import PanelManager

logger = structlog.get_logger(__name__)


class Panel(models.Model):
    """Физическая панель LED-экрана."""

    objects = PanelManager()

    name = models.CharField(max_length=15, unique=True, verbose_name="идентификатор")
    display = models.ForeignKey(
        "directory_displays.Display",
        on_delete=models.PROTECT,
        null=True,
        verbose_name="установлен на",
    )
    comment = models.TextField(blank=True, null=True, verbose_name="описание")
    condition = models.ForeignKey(
        "core_references.Condition",
        on_delete=models.PROTECT,
        null=True,
        verbose_name="состояние",
        default="work",
    )
    department = models.ForeignKey(
        "core_references.Department",
        on_delete=models.PROTECT,
        null=True,
        verbose_name="нахождение",
        default="zip",
    )
    # T-2-028: application_status больше не хранится в БД — вычисляется через property.
    # Поле закомментировано — физическое удаление колонки в отдельной миграции
    # после того как весь код переведён на property.
    # application_status = models.ForeignKey(...) # DEPRECATED — используй active_application_status

    class Meta:
        app_label = "directory_panels"
        db_table = "panel"
        verbose_name = "Панель"
        verbose_name_plural = "Панели"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.name


    @property
    def active_application(self):
        """Активная (не архивная) заявка на эту панель, или None."""
        # Lazy import — circular dependency с workflow
        from django.apps import apps
        Application = apps.get_model("workflow_applications", "Application")
        return (
            Application.objects
            .filter(panel=self)
            .exclude(status__name__in=["archive_done", "archive_unable"])
            .order_by("-last_update_date_time")
            .first()
        )

    @property
    def application_status(self):
        """
        ApplicationStatus активной заявки, или 'default' если заявок нет.

        T-2-028: вычисляемое свойство вместо денормализованного поля.
        Для queryset — используй .with_application_status() (без N+1).
        """
        app = self.active_application
        if app:
            return app.status
        from django.apps import apps
        ApplicationStatus = apps.get_model("workflow_applications", "ApplicationStatus")
        return ApplicationStatus.objects.filter(name="default").first()

    @property
    def has_active_application(self) -> bool:
        """Есть ли незакрытая заявка на панель."""
        return self.active_application is not None

    def get_full_title(self) -> str:
        display_name = self.display.name if self.display else None
        comment = self.comment or "Не передан"
        condition = self.condition.description if self.condition else "—"
        department = self.department.description if self.department else "—"
        app_status = (
            self.application_status.description
            if self.application_status and self.application_status.name != "default"
            else None
        )
        parts = [f"ID - {self.name}"]
        if display_name:
            parts.append(f"Экран - {display_name}")
        parts.append(f"Комментарий - {comment}")
        parts.append(f"Состояние - {condition}")
        if app_status:
            parts.append(f"Заявка - {app_status}")
        parts.append(f"Нахождение - {department}")
        return "\n".join(parts)

    @property
    def active_application(self):
        """Активная (не архивная) заявка на этой панели, или None."""
        # Используем apps.get_model чтобы избежать circular imports
        from django.apps import apps
        Application = apps.get_model("workflow_applications", "Application")
        return (
            Application.objects
            .filter(panel=self)
            .exclude(status__name__in=("archive_done", "archive_unable"))
            .select_related("status")
            .order_by("-last_update_date_time")
            .first()
        )

    @property
    def active_application_status(self):
        """
        ApplicationStatus активной заявки, или 'default' если заявок нет.
        T-2-028: заменяет денормализованное поле application_status.
        """
        app = self.active_application
        if app:
            return app.status
        # Возвращаем фиктивный объект со статусом default
        from django.apps import apps
        ApplicationStatus = apps.get_model("workflow_applications", "ApplicationStatus")
        return ApplicationStatus.objects.filter(name="default").first()

    @property
    def has_active_application(self) -> bool:
        """Есть ли активная (не архивная) заявка на эту панель."""
        return self.active_application is not None


# Compat alias — старые импорты `from zip.models import Panels` работают
Panels = Panel
