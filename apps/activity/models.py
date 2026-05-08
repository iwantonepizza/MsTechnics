"""
apps/activity/models.py — единый журнал событий ActivityLog.

T-2-022: заменяет 5 таблиц-историй:
  - ApplicationHistoryReport
  - PanelHistoryReport
  - DisplayHistoryReport
  - DepartureHistoryReport
  - DailyTaskHistoryReport

Использует GenericForeignKey для привязки к любому объекту.
"""
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

EVENT_TYPE_CHOICES = [
    # Панели
    ("panel_move", "Панель: перемещение"),
    ("panel_breakdown", "Панель: поломка"),
    ("panel_condition_change", "Панель: смена состояния"),
    ("panel_service", "Панель: сервисные работы"),
    ("panel_comment", "Панель: комментарий"),
    # Заявки
    ("application_create", "Заявка: создана"),
    ("application_transition", "Заявка: смена статуса"),
    ("application_delete", "Заявка: удалена"),
    ("application_executor_change", "Заявка: смена исполнителя"),
    # Выезды
    ("departure_create", "Выезд: создан"),
    ("departure_complete", "Выезд: выполнен"),
    ("departure_archive", "Выезд: архивирован"),
    # Экраны
    ("display_panel_replace", "Экран: замена панели"),
    # Ежедневные задания
    ("daily_task_complete", "Задание: выполнено"),
    ("daily_task_reset", "Задание: сброшено"),
    # Системные
    ("system", "Системное"),
]


class ActivityLogManager(models.Manager):
    def for_target(self, obj):
        """Все события для конкретного объекта."""
        ct = ContentType.objects.get_for_model(obj)
        return self.filter(target_type=ct, target_id=obj.pk)

    def for_display(self, display):
        """Все события связанные с экраном (прямо или через панели)."""
        from apps.directory.displays.models import Display
        ct = ContentType.objects.get_for_model(Display)
        return self.filter(target_type=ct, target_id=display.pk)


class ActivityLog(models.Model):
    """
    Единая запись журнала событий.

    Может быть привязана к любому объекту через GenericForeignKey:
    панель, экран, заявка, выезд.
    """

    objects = ActivityLogManager()

    # Кто совершил действие
    actor = models.ForeignKey(
        "user.MsUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="исполнитель",
        related_name="activity_log",
    )
    actor_name = models.CharField(
        max_length=80,
        blank=True,
        verbose_name="имя исполнителя (snapshot)",
        help_text="Строковый снимок — история сохраняется даже если юзер удалён",
    )

    # На что направлено действие
    target_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="тип объекта",
    )
    target_id = models.PositiveIntegerField(null=True, blank=True, verbose_name="ID объекта")
    target = GenericForeignKey("target_type", "target_id")

    # Что произошло
    event_type = models.CharField(
        max_length=40,
        choices=EVENT_TYPE_CHOICES,
        verbose_name="тип события",
    )
    description = models.TextField(blank=True, verbose_name="описание")
    comment = models.TextField(blank=True, verbose_name="комментарий")
    payload = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="доп. данные",
        help_text="from_department, to_department, old_condition, etc.",
    )

    # Когда
    occurred_at = models.DateTimeField(default=timezone.now, verbose_name="время события", db_index=True)

    # Технические поля
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP адрес")

    class Meta:
        app_label = "activity"
        db_table = "activity_log"
        verbose_name = "Запись журнала"
        verbose_name_plural = "Журнал событий"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["target_type", "target_id"], name="activity_target_idx"),
            models.Index(fields=["event_type"], name="activity_event_type_idx"),
            models.Index(fields=["actor"], name="activity_actor_idx"),
        ]

    def __str__(self) -> str:
        actor = self.actor_name or "system"
        return f"[{self.event_type}] {actor} @ {self.occurred_at:%d.%m.%Y %H:%M}"
