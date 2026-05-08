"""
apps/directory/storage/models.py — расходники ЗИП: провода, хабы, ламели.

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
    description = models.CharField(max_length=100, blank=True, null=True, verbose_name="Описание")
    count = models.PositiveIntegerField(
        default=0, verbose_name="Количество", validators=[validate_non_negative]
    )
    photo = models.ImageField(upload_to="photos/", blank=True, null=True, verbose_name="Фото")

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return self.name

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
        verbose_name = "Провод"
        verbose_name_plural = "Провода"
        ordering = ["id"]


class Hubs(StorageItemMixin):
    class Meta:
        app_label = "directory_storage"
        db_table = "hubs_zip"
        verbose_name = "Хаб"
        verbose_name_plural = "Хабы"
        ordering = ["id"]


class Lamels(StorageItemMixin):
    class Meta:
        app_label = "directory_storage"
        db_table = "lamels_storage"
        verbose_name = "Ламель"
        verbose_name_plural = "Ламели"
        ordering = ["id"]
