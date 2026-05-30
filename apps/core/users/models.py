"""
apps/core/users/models.py — кастомная модель пользователя.

T-2-012: перенесено из user/models.py.
T-2-026: ConcreteMsUser удалён.
label = "user" — оставляем для совместимости с AUTH_USER_MODEL = "user.MsUser"
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.Model):
    name = models.CharField(max_length=32, unique=True)
    description = models.CharField(max_length=128, blank=True)

    class Meta:
        db_table = "role"
        verbose_name = "Роль"
        verbose_name_plural = "Роли"

    def __str__(self) -> str:
        return self.name


class MsUser(AbstractUser):
    TYPE_PERMISSION = [
        ("monitoring", "Мониторинг"),
        ("control", "Контроль"),
        ("service", "Сервис"),
        ("all", "Все"),
        ("admin", "Админ"),
        ("technical", "Техник"),
        ("none_type", "Никакие"),
    ]

    permission = models.CharField(
        max_length=20,
        choices=TYPE_PERMISSION,
        default="none_type",
        verbose_name="Уровень доступа",
    )
    allowed_city = models.ManyToManyField(
        "core_references.Cities",
        blank=True,
        verbose_name="Разрешённые города",
    )
    roles = models.ManyToManyField(
        Role,
        related_name="users",
        blank=True,
        verbose_name="Роли",
    )
    extra_permissions = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Дополнительные права",
    )
    show_activity_feed = models.BooleanField(
        default=False,
        verbose_name="Показывать ленту действий на главной",
        help_text="T-8-020: включает блок «Последние действия» на главном экране для этого пользователя.",
    )
    telegram_id = models.CharField(
        max_length=20,  # расширили с 10 до 20 — telegram_id бывает длиннее
        blank=True,
        null=True,
        verbose_name="Айди Telegram",
    )
    max_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Айди MAX (VK мессенджер)",
    )

    class Meta:
        app_label = "user"       # ← label=user для AUTH_USER_MODEL совместимости
        db_table = "user"
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self) -> str:
        return self.username

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.username
