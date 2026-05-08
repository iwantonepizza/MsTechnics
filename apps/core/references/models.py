"""
apps/core/references/models.py — справочники: цвета, иконки, города, состояния, отделы.

T-2-012: перенесено из main/models.py.
КРИТИЧНО: db_table у всех моделей совпадает с оригинальными — данные в БД не трогаем.
Миграции используют SeparateDatabaseAndState — таблицы уже существуют.
"""
from django.db import models


class Cities(models.Model):
    name = models.CharField(max_length=15, unique=True, verbose_name="имя")
    slug = models.SlugField(unique=True, blank=True, null=True, verbose_name="URL")
    description = models.TextField(blank=True, null=True, verbose_name="описание")

    class Meta:
        app_label = "core_references"
        db_table = "city"  # ← оригинальная таблица, не трогаем
        verbose_name = "Город"
        verbose_name_plural = "Города"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.name


class Color(models.Model):
    name = models.CharField(max_length=15, unique=True, verbose_name="Цвет")
    hex_color = models.CharField(max_length=7, unique=True, verbose_name="Код цвета")

    class Meta:
        app_label = "core_references"
        db_table = "color"
        verbose_name = "Цвет"
        verbose_name_plural = "Цвета"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.name


class Smile(models.Model):
    """Иконка/эмодзи для статусов, состояний, событий."""

    smile_icon = models.CharField(max_length=15, unique=True, verbose_name="Иконка")

    class Meta:
        app_label = "core_references"
        db_table = "smile"
        verbose_name = "Иконка"
        verbose_name_plural = "Иконки"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.smile_icon


class Condition(models.Model):
    """Состояние панели: work / error / unrecoverable / default."""

    name = models.CharField(max_length=15, unique=True, verbose_name="Состояние")
    description = models.TextField(blank=True, null=True, verbose_name="описание")
    color = models.ForeignKey(
        "Color",
        on_delete=models.PROTECT,
        verbose_name="цвет фона",
        related_name="condition_color",
    )
    color_text = models.ForeignKey(
        "Color",
        on_delete=models.PROTECT,
        verbose_name="цвет текста",
        related_name="condition_color_text",
    )
    icon = models.ForeignKey(
        "Smile",
        on_delete=models.PROTECT,
        null=True,
        verbose_name="иконка",
    )

    class Meta:
        app_label = "core_references"
        db_table = "condition"
        verbose_name = "Состояние"
        verbose_name_plural = "Состояния"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.name


class Department(models.Model):
    """Отдел: monitoring / control / service / zip / hand."""

    name = models.CharField(max_length=20, unique=True, verbose_name="название отдела")
    description = models.TextField(blank=True, null=True, verbose_name="описание")
    color = models.ForeignKey(
        "Color",
        on_delete=models.PROTECT,
        verbose_name="цвет",
        related_name="department_color",
    )
    color_text = models.ForeignKey(
        "Color",
        on_delete=models.PROTECT,
        verbose_name="цвет текста",
        related_name="department_color_text",
    )
    icon = models.ForeignKey(
        "Smile",
        on_delete=models.PROTECT,
        null=True,
        verbose_name="иконка",
    )

    class Meta:
        app_label = "core_references"
        db_table = "department"
        verbose_name = "Отдел"
        verbose_name_plural = "Отделы"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.name
