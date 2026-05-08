from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class NotificationTemplate(models.Model):
    name = models.CharField(max_length=64, unique=True, db_index=True)
    description = models.CharField(max_length=200, blank=True)
    text = models.TextField(help_text="Text with {placeholders} rendered from context")

    class Meta:
        db_table = "notification_template"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Notification(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "В очереди"
        SENT = "sent", "Отправлено"
        FAILED = "failed", "Ошибка"
        SKIPPED = "skipped", "Пропущено"

    template = models.ForeignKey(NotificationTemplate, on_delete=models.PROTECT)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    rendered_text = models.TextField(blank=True)
    context = models.JSONField(default=dict, blank=True)
    related_target_ct = models.ForeignKey(
        ContentType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    related_target_id = models.CharField(max_length=64, null=True, blank=True)
    related_target = GenericForeignKey("related_target_ct", "related_target_id")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    primary_channel = models.CharField(max_length=16, blank=True)
    delivered_via = models.CharField(max_length=16, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notification"
        indexes = [
            models.Index(fields=["recipient", "status", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Notification #{self.pk} to {self.recipient_id}"


class NotificationDeliveryAttempt(models.Model):
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    channel = models.CharField(max_length=16)
    attempted_at = models.DateTimeField(auto_now_add=True)
    succeeded = models.BooleanField()
    error_message = models.TextField(blank=True)
    response_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "notification_delivery_attempt"
        ordering = ["attempted_at", "id"]

    def __str__(self) -> str:
        return f"{self.channel}: {'ok' if self.succeeded else 'failed'}"
