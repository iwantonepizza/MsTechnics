"""
apps/workflow/departures/models.py — выезды и исполнители.

T-2-014: перенесено из departure/models.py.
T-2-030: Departure.status CharField → FK(DepartureStatus).
db_table сохранены ('departure', 'executor', 'departure_status').
"""
from django.db import models


class Executor(models.Model):
    first_name = models.CharField(max_length=150, blank=True, verbose_name="Имя")
    last_name = models.CharField(max_length=150, blank=True, verbose_name="Фамилия")
    executor_role = models.CharField(max_length=20, default="должности нет", verbose_name="Должность")
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="Телефон")
    telegram_id = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telegram ID")

    class Meta:
        app_label = "workflow_departures"
        db_table = "executor"
        verbose_name = "Исполнитель"
        verbose_name_plural = "Исполнители"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


class DepartureStatus(models.Model):
    """
    T-2-030: справочник статусов выездов.
    Заменяет CharField со свободными русскими значениями.
    """

    name = models.CharField(max_length=40, unique=True, verbose_name="код")
    description = models.CharField(max_length=80, verbose_name="название для UI")
    color = models.ForeignKey(
        "core_references.Color",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="цвет",
    )
    icon = models.ForeignKey(
        "core_references.Smile",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="иконка",
    )
    order = models.PositiveSmallIntegerField(default=0, verbose_name="порядок")
    is_terminal = models.BooleanField(default=False, verbose_name="терминальный")

    class Meta:
        app_label = "workflow_departures"
        db_table = "departure_status"
        verbose_name = "Статус выезда"
        verbose_name_plural = "Статусы выездов"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.description


# Имена статусов — константы для использования в коде (вместо русских строк)
class DepartureStatusName:
    CREATED = "created"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Departure(models.Model):
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    user_create = models.CharField(max_length=20, verbose_name="Создатель")
    time_updated = models.DateTimeField(blank=True, null=True, verbose_name="Последнее взаимодействие")
    time_created = models.DateTimeField(blank=True, null=True, verbose_name="Время создания")
    time_start = models.DateTimeField(blank=True, null=True, verbose_name="Начало выезда")
    time_end = models.DateTimeField(blank=True, null=True, verbose_name="Окончание выезда")
    result = models.TextField(blank=True, null=True, verbose_name="Результат")
    executor = models.ForeignKey(
        "Executor",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        verbose_name="Исполнитель",
    )
    notification = models.JSONField(blank=True, null=True, verbose_name="Уведомления")

    # T-2-030: FK вместо CharField
    status = models.ForeignKey(
        "DepartureStatus",
        on_delete=models.PROTECT,
        null=True,  # null=True пока backfill не завершён → потом NOT NULL
        verbose_name="Статус",
        related_name="departures",
    )

    # T-2-030: legacy CharField — оставляем до завершения backfill
    status_legacy = models.CharField(
        max_length=40,
        blank=True,
        default="",
        verbose_name="Статус (legacy, удалить после backfill)",
        db_column="status",
    )

    class Meta:
        app_label = "workflow_departures"
        db_table = "departure"
        verbose_name = "Выезд"
        verbose_name_plural = "Выезды"
        ordering = ["id"]

    def __str__(self) -> str:
        return str(self.description)

    # ─── Удобные свойства вместо сравнения с русскими строками ───────────

    @property
    def is_created(self) -> bool:
        return bool(self.status and self.status.name == DepartureStatusName.CREATED)

    @property
    def is_completed(self) -> bool:
        return bool(self.status and self.status.name == DepartureStatusName.COMPLETED)

    @property
    def is_archived(self) -> bool:
        return bool(self.status and self.status.name == DepartureStatusName.ARCHIVED)

    @property
    def is_terminal(self) -> bool:
        return bool(self.status and self.status.is_terminal)



class Contact(models.Model):
    """
    Контактное лицо на экране (мастер, электрик, охрана и т.д.).
    T-2-fix-001: восстановлено (отсутствовало в compat shim → django check падал).
    """
    first_name = models.CharField(max_length=150, blank=True, verbose_name="Имя")
    last_name = models.CharField(max_length=150, blank=True, verbose_name="Фамилия")
    description = models.CharField(max_length=150, blank=True, verbose_name="Описание")
    displays = models.ManyToManyField(
        "directory_displays.Display",
        related_name="contacts",
        verbose_name="Список экранов",
        blank=True,
    )
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="Телефон")
    telegram_id = models.CharField(max_length=15, blank=True, null=True, verbose_name="Telegram ID")

    class Meta:
        app_label = "workflow_departures"
        db_table = "contact"
        verbose_name = "Контакт"
        verbose_name_plural = "Контакты"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} {self.phone_number}"


class DepartureHistoryReport(models.Model):
    """Legacy-история выездов. Будет заменена ActivityLog в T-2-022/024."""

    departure = models.ForeignKey(
        "Departure", on_delete=models.SET_NULL, null=True, verbose_name="Выезд"
    )
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    comment = models.TextField(verbose_name="Комментарий")
    time = models.DateTimeField(verbose_name="Время")
    user = models.ForeignKey(
        "user.MsUser", on_delete=models.PROTECT, null=True, verbose_name="Работник"
    )

    class Meta:
        app_label = "workflow_departures"
        db_table = "departure_history_report"
        verbose_name = "История выезда (legacy)"
        verbose_name_plural = "История выездов (legacy)"
        ordering = ["id"]

    def __str__(self) -> str:
        return str(self.description)
