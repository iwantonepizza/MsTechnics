"""
apps/workflow/applications/models.py — заявки и их статусы.

T-2-014: перенесено из application/models.py.
T-2-020: добавлена модель ApplicationEvent (денормализация 28 полей).
db_table сохранены ('application', 'application_status').
"""
from django.db import models
from django.utils import timezone

from apps.workflow.applications.managers import ApplicationManager


class ApplicationStatus(models.Model):
    name = models.TextField(max_length=40, unique=True, verbose_name="название")
    description = models.TextField(blank=True, null=True, verbose_name="описание")
    color = models.ForeignKey(
        "core_references.Color",
        on_delete=models.PROTECT,
        verbose_name="цвет",
        related_name="application_status_color",
    )
    color_text = models.ForeignKey(
        "core_references.Color",
        on_delete=models.PROTECT,
        verbose_name="цвет текста",
        related_name="application_status_color_text",
    )
    icon = models.ForeignKey(
        "core_references.Smile",
        on_delete=models.PROTECT,
        null=True,
        verbose_name="иконка",
    )

    class Meta:
        app_label = "workflow_applications"
        db_table = "application_status"
        verbose_name = "Статус заявки"
        verbose_name_plural = "Статусы заявок"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.name


class Application(models.Model):
    objects = ApplicationManager()

    display = models.ForeignKey(
        "directory_displays.Display",
        on_delete=models.PROTECT,
        null=True,
        verbose_name="экран",
        related_name="application",
    )
    panel = models.ForeignKey(
        "directory_panels.Panel",
        on_delete=models.PROTECT,
        null=True,
        verbose_name="панель",
        related_name="application",
    )
    status = models.ForeignKey(
        "ApplicationStatus",
        on_delete=models.PROTECT,
        null=False,
        verbose_name="Статус",
        related_name="application",
    )
    cell = models.ForeignKey(
        "directory_displays.Cell",
        on_delete=models.PROTECT,
        null=False,
        verbose_name="ячейка",
    )
    executor = models.ForeignKey(
        "workflow_departures.Executor",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        verbose_name="Исполнитель",
    )
    last_update_date_time = models.DateTimeField(
        verbose_name="Время последней активности", null=True, blank=True
    )

    # ── Legacy-поля (28 штук) ─────────────────────────────────────────────
    # Оставлены для обратной совместимости фронта.
    # T-2-020: данные мигрированы в ApplicationEvent.
    # T-2-021: поля будут удалены через ~2 недели после T-2-020.
    comment_monitoring = models.TextField(max_length=300, null=True, verbose_name="Коммент мониторинга")
    time_monitoring = models.DateTimeField(null=True, blank=True)
    file_monitoring = models.FileField(upload_to="application/", blank=True, null=True)
    user_monitoring = models.CharField(max_length=40, blank=True, null=True)

    comment_control_apply = models.TextField(max_length=300, null=True)
    time_control_apply = models.DateTimeField(null=True, blank=True)
    file_control_apply = models.FileField(upload_to="files/", blank=True, null=True)
    user_control_apply = models.CharField(max_length=40, blank=True, null=True)

    comment_control_send = models.TextField(max_length=300, null=True)
    time_control_send = models.DateTimeField(null=True, blank=True)
    file_control_send = models.FileField(upload_to="files/", blank=True, null=True)
    user_control_send = models.CharField(max_length=40, blank=True, null=True)

    comment_service_apply = models.TextField(max_length=300, null=True)
    time_service_apply = models.DateTimeField(null=True, blank=True)
    file_service_apply = models.FileField(upload_to="files/", blank=True, null=True)
    user_service_apply = models.CharField(max_length=40, blank=True, null=True)

    comment_control_at_work = models.TextField(max_length=300, null=True)
    time_control_at_work = models.DateTimeField(null=True, blank=True)
    file_control_at_work = models.FileField(upload_to="files/", blank=True, null=True)
    user_control_at_work = models.CharField(max_length=40, blank=True, null=True)

    comment_control_unable = models.TextField(max_length=300, null=True)
    time_control_unable = models.DateTimeField(null=True, blank=True)
    file_control_unable = models.FileField(upload_to="files/", blank=True, null=True)
    user_control_unable = models.CharField(max_length=40, blank=True, null=True)

    comment_control_archive = models.TextField(max_length=300, null=True)
    time_control_archive = models.DateTimeField(null=True, blank=True)
    file_control_archive = models.FileField(upload_to="files/", blank=True, null=True)
    user_control_archive = models.CharField(max_length=40, blank=True, null=True)

    class Meta:
        app_label = "workflow_applications"
        db_table = "application"
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"Заявка #{self.id}"


# ─── T-2-020: ApplicationEvent ────────────────────────────────────────────
STAGE_CHOICES = [
    ("monitoring_create", "Создана мониторингом"),
    ("control_apply", "Принята контролем"),
    ("control_send", "Отправлена в сервис"),
    ("service_apply", "Принята сервисом"),
    ("service_complete", "Ремонт выполнен"),
    ("service_unable", "Ремонт невозможен"),
    ("archive_done", "Архивирована (выполнена)"),
    ("archive_unable", "Архивирована (невозможно)"),
]


class ApplicationEvent(models.Model):
    """
    Событие жизненного цикла заявки.

    T-2-020: заменяет 28 денормализованных полей (comment_*, time_*, user_*, file_*).
    Каждое действие = одна строка с stage, comment, actor, occurred_at.
    """

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name="заявка",
    )
    stage = models.CharField(
        max_length=30,
        choices=STAGE_CHOICES,
        verbose_name="этап",
    )
    comment = models.TextField(blank=True, null=True, verbose_name="комментарий")
    file = models.FileField(upload_to="application/events/", blank=True, null=True, verbose_name="файл")
    actor = models.ForeignKey(
        "user.MsUser",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="исполнитель",
        related_name="application_events",
    )
    actor_name = models.CharField(
        max_length=80,
        blank=True,
        verbose_name="имя исполнителя (snapshot)",
        help_text="Сохраняем как строку — если юзер удалён, история сохраняется",
    )
    occurred_at = models.DateTimeField(default=timezone.now, verbose_name="время события")

    class Meta:
        app_label = "workflow_applications"
        db_table = "application_event"
        verbose_name = "Событие заявки"
        verbose_name_plural = "События заявок"
        ordering = ["occurred_at"]

    def __str__(self) -> str:
        return f"{self.application_id} / {self.stage} / {self.occurred_at:%d.%m.%Y %H:%M}"


# Legacy история (оставляем пока T-2-024 не удалит)
class ApplicationHistoryReport(models.Model):
    application_id = models.CharField(max_length=5, null=True, verbose_name="ID заявки")
    description = models.TextField(blank=True, null=True)
    comment = models.TextField(verbose_name="комментарий")
    time = models.DateTimeField(verbose_name="время")
    user = models.CharField(max_length=40, verbose_name="пользователь")

    class Meta:
        app_label = "workflow_applications"
        db_table = "history_application"
        verbose_name = "История заявки (legacy)"
        verbose_name_plural = "История заявок (legacy)"
        ordering = ["id"]

    def __str__(self) -> str:
        return str(self.description)
