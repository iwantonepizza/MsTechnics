from __future__ import annotations

from django.db import models


class AlarmEvent(models.Model):
    class Type(models.TextChoices):
        FAULTY = "faulty", "Аварийное"
        RECOVERY = "recovery", "Восстановление"

    type = models.CharField(max_length=10, choices=Type.choices, db_index=True)
    display = models.ForeignKey(
        "directory_displays.Display",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vnnox_alarms",
    )
    cell = models.ForeignKey(
        "directory_displays.Cell",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    panel = models.ForeignKey(
        "directory_panels.Panel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    device_id = models.CharField(max_length=64, db_index=True)
    screen_name_raw = models.CharField(max_length=200)
    receiving_card_no = models.PositiveIntegerField()
    raw_position = models.CharField(max_length=300, blank=True)
    raw_email_subject = models.CharField(max_length=300, blank=True)
    gmail_message_id = models.CharField(max_length=100, blank=True, db_index=True)
    occurred_at = models.DateTimeField(db_index=True)
    received_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True, db_index=True)
    resolved_by_alarm = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resolves",
    )

    class Meta:
        db_table = "alarm_event"
        indexes = [
            models.Index(fields=["device_id", "receiving_card_no", "-occurred_at"]),
            models.Index(fields=["display", "resolved_at", "-occurred_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["gmail_message_id", "type", "device_id", "receiving_card_no", "occurred_at"],
                name="unique_vnnox_alarm_from_email",
            )
        ]
        ordering = ["-occurred_at", "-id"]

    def __str__(self) -> str:
        return f"{self.type} {self.device_id} RC {self.receiving_card_no}"
