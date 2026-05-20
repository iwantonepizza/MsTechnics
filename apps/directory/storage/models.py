"""
apps/directory/storage/models.py — расходники ЗИП: провода, хабы, ламели,
блоки питания и коннекторы.

T-2-013: перенесено из zip/models.py.
db_table сохранены ('wires_zip', 'hubs_zip', 'lamels_storage').
"""

from django.core.exceptions import ValidationError
from django.db import models


def validate_non_negative(value: int) -> None:
    if value < 0:
        raise ValidationError("Количество не может быть меньше нуля.")


class StorageItemMixin(models.Model):
    """Базовый класс для расходников ЗИП."""

    name = models.CharField(max_length=20, unique=True, verbose_name="Имя")
    description = models.CharField(  # noqa: DJ001
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Описание",
    )
    count = models.PositiveIntegerField(
        default=0, verbose_name="Количество", validators=[validate_non_negative]
    )
    low_stock_threshold = models.PositiveIntegerField(
        default=3,
        verbose_name="Порог низкого остатка",
    )
    photo = models.ImageField(upload_to="photos/", blank=True, null=True, verbose_name="Фото")

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return self.name

    @property
    def is_low_stock(self) -> bool:
        return self.count < self.low_stock_threshold

    def increase_count(self, value: int = 1) -> None:
        if value < 0:
            raise ValueError("Значение для увеличения должно быть положительным")
        self.count += value
        self.save()

    def decrease_count(self, value: int = 1) -> None:
        if value < 0:
            raise ValueError("Значение для уменьшения должно быть положительным")
        if self.count - value < 0:
            raise ValidationError("Количество не может быть меньше нуля.")
        self.count -= value
        self.save()


class Wires(StorageItemMixin):
    class Meta:
        app_label = "directory_storage"
        db_table = "wires_zip"
        permissions = [("can_edit_zip_counts", "Can edit ZIP counts for storage items")]
        verbose_name = "Провод"
        verbose_name_plural = "Провода"
        ordering = ["id"]


class Hubs(StorageItemMixin):
    class Meta:
        app_label = "directory_storage"
        db_table = "hubs_zip"
        verbose_name = "Хаб"  # noqa: RUF001
        verbose_name_plural = "Хабы"
        ordering = ["id"]


class Lamels(StorageItemMixin):
    class Meta:
        app_label = "directory_storage"
        db_table = "lamels_storage"
        verbose_name = "Ламель"
        verbose_name_plural = "Ламели"
        ordering = ["id"]


class PowerBlocks(StorageItemMixin):
    class Meta:
        app_label = "directory_storage"
        db_table = "power_blocks_zip"
        verbose_name = "Блок питания"
        verbose_name_plural = "Блоки питания"
        ordering = ["id"]


class Connectors(StorageItemMixin):
    class Meta:
        app_label = "directory_storage"
        db_table = "connectors_zip"
        verbose_name = "Коннектор"
        verbose_name_plural = "Коннекторы"
        ordering = ["id"]
