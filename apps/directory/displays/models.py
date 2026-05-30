"""
apps/directory/displays/models.py — Display и Cell.

T-2-013: перенесено из zip/models.py.
КРИТИЧНО: db_table сохранены ('display', 'cell').
Display.save() с side effects оставлен как есть — рефакторинг в T-2-027.
"""
from django.apps import apps
from django.db import models
from django.db.models import UniqueConstraint

import structlog

logger = structlog.get_logger(__name__)


CONDITION_SEVERITY = {
    "work": 10,
    "default": 20,
    "problem": 30,
    "error": 30,
    "broken": 30,
    "unrecoverable": 40,
}


def condition_severity(condition) -> tuple[int, int]:
    if condition is None:
        return (-1, -1)
    return (CONDITION_SEVERITY.get(condition.name, 0), condition.id)


class Display(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name="экран")
    city = models.ForeignKey(
        "core_references.Cities",
        on_delete=models.PROTECT,
        verbose_name="город",
        related_name="display",
    )
    description = models.TextField(blank=True, null=True, verbose_name="описание")
    rows = models.PositiveIntegerField(verbose_name="кол-во рядов", default=0)
    cols = models.PositiveIntegerField(verbose_name="кол-во столбцов", default=0)
    camera_link = models.URLField(max_length=150, null=True, verbose_name="ссылка на камеру")
    file = models.FileField(
        upload_to="files/", blank=True, null=True, verbose_name="Электросхема"
    )
    project_photo = models.FileField(
        upload_to="files/", blank=True, null=True, verbose_name="Проект"
    )
    slug = models.SlugField(unique=True, blank=True, null=True, verbose_name="URL")
    vnnox_device_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        verbose_name="VNNOX device id",
        help_text="Серийник VNNOX для маппинга email-алармов",
    )

    class Meta:
        app_label = "directory_displays"
        db_table = "display"
        verbose_name = "Экран"
        verbose_name_plural = "Экраны"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.name

    @property
    def cells(self):
        return self.cell_set.all()

    @property
    def current_condition(self):
        """Возвращает наихудшее состояние среди всех панелей экрана."""
        Condition = apps.get_model("core_references", "Condition")
        worst_condition = None
        for condition in (
            Condition.objects.filter(id__in=self.cell_set.values_list("panel__condition_id", flat=True))
            .only("id", "name")
        ):
            if condition_severity(condition) > condition_severity(worst_condition):
                worst_condition = condition
        if worst_condition is not None:
            return worst_condition
        return None

    def save(self, *args, **kwargs):
        """
        T-2-027: side-effects (cells, panels, history) вынесены в
        DisplayService.create_with_layout().
        Здесь стандартное Django-поведение.
        """
        super().save(*args, **kwargs)


class Cell(models.Model):
    display = models.ForeignKey(
        "Display",
        on_delete=models.CASCADE,
        related_name="cell_set",
        verbose_name="экран",
        editable=False,
    )
    row = models.PositiveIntegerField(verbose_name="ряд", editable=False)
    col = models.PositiveIntegerField(verbose_name="столбец", editable=False)
    panel = models.ForeignKey(
        "directory_panels.Panel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cell",
        verbose_name="панель",
    )

    class Meta:
        app_label = "directory_displays"
        db_table = "cell"
        constraints = [
            UniqueConstraint(fields=["panel"], name="unique_panel"),
            UniqueConstraint(fields=["display", "row", "col"], name="unique_display_row_col"),
        ]
        verbose_name = "Ячейка"
        verbose_name_plural = "Ячейки"
        ordering = ["display", "row", "col"]

    def __str__(self) -> str:
        return f"Ячейка {self.position} на {self.display.name}"

    @property
    def position(self) -> str | None:
        if not self.display:
            return None
        pos = (self.row - 1) * self.display.cols + self.col
        return str(pos).zfill(2)


class PhotoDisplay(models.Model):
    display = models.ForeignKey(
        "Display",
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name="Экран",
    )
    image = models.ImageField(upload_to="photos/display_photos/", verbose_name="Фото")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        app_label = "directory_displays"
        db_table = "photo_display"
        verbose_name = "Фото экрана"
        verbose_name_plural = "Фото экрана"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"Фото {self.display.name}"
