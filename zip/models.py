"""Compat proxies for legacy `zip` imports and string relations."""

from django.core.exceptions import ValidationError

from apps.core.references.models import Condition, Department
from apps.directory.displays.models import Cell as DirectoryCell
from apps.directory.displays.models import Display as DirectoryDisplay
from apps.directory.displays.models import PhotoDisplay as DirectoryPhotoDisplay
from apps.directory.panels.models import Panel as DirectoryPanel
from apps.directory.storage.models import Hubs as DirectoryHubs
from apps.directory.storage.models import Lamels as DirectoryLamels
from apps.directory.storage.models import Wires as DirectoryWires
from apps.workflow.daily_tasks.models import DailyTask as WorkflowDailyTask


class Display(DirectoryDisplay):
    class Meta:
        proxy = True
        app_label = "zip"
        verbose_name = "Экран"
        verbose_name_plural = "Экраны"


class Cell(DirectoryCell):
    class Meta:
        proxy = True
        app_label = "zip"
        verbose_name = "Ячейка"
        verbose_name_plural = "Ячейки"


class Panels(DirectoryPanel):
    class Meta:
        proxy = True
        app_label = "zip"
        verbose_name = "Панель"
        verbose_name_plural = "Панели"


class DailyTask(WorkflowDailyTask):
    class Meta:
        proxy = True
        app_label = "zip"
        verbose_name = "Задание"
        verbose_name_plural = "Задания"


def validate_positive(value):
    if value < 0:
        raise ValidationError("Количество не может быть меньше нуля.")


class Wires(DirectoryWires):
    class Meta:
        proxy = True
        app_label = "zip"
        verbose_name = "Провод"
        verbose_name_plural = "Провода"


class Hubs(DirectoryHubs):
    class Meta:
        proxy = True
        app_label = "zip"
        verbose_name = "Хаб"
        verbose_name_plural = "Хабы"


class Lamels(DirectoryLamels):
    class Meta:
        proxy = True
        app_label = "zip"
        verbose_name = "Ламель"
        verbose_name_plural = "Ламели"


class PhotoDisplay(DirectoryPhotoDisplay):
    class Meta:
        proxy = True
        app_label = "zip"
        verbose_name = "Фото экрана"
        verbose_name_plural = "Фото экрана"


Panel = Panels

__all__ = [
    "Cell",
    "Condition",
    "DailyTask",
    "Department",
    "Display",
    "Hubs",
    "Lamels",
    "Panel",
    "Panels",
    "PhotoDisplay",
    "Wires",
    "validate_positive",
]
