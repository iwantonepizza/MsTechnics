from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail

from .base import BaseChannel, DeliveryResult


class EmailChannel(BaseChannel):
    name = "email"

    def can_deliver(self, recipient) -> bool:
        return bool(getattr(recipient, "email", None))

    def deliver(self, recipient, text: str, *, context: dict | None = None) -> DeliveryResult:
        try:
            sent = send_mail(
                subject="[MsTechnics] Уведомление",
                message=text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                fail_silently=False,
            )
            return {
                "succeeded": sent > 0,
                "error": None if sent else "send_mail returned 0",
                "response": {"sent_count": sent},
            }
        except Exception as exc:
            return {"succeeded": False, "error": str(exc), "response": {}}
