from __future__ import annotations

from collections.abc import Iterable

import structlog
from django.utils import timezone

from shared.metrics import notification_all_channels_failed_total, notification_delivery_total

from .channels import BaseChannel, EmailChannel, MaxChannel, TelegramChannel
from .models import Notification, NotificationDeliveryAttempt

logger = structlog.get_logger(__name__)


class NotificationDispatcher:
    DEFAULT_FALLBACK_ORDER = ("telegram", "max", "email")

    def __init__(self, channels: Iterable[BaseChannel] | None = None):
        configured_channels = channels or [
            TelegramChannel(),
            MaxChannel(),
            EmailChannel(),
        ]
        self.channels = {channel.name: channel for channel in configured_channels}

    def dispatch(
        self,
        notification: Notification,
        fallback_order: tuple[str, ...] | None = None,
    ) -> bool:
        order = fallback_order or self.DEFAULT_FALLBACK_ORDER

        for channel_name in order:
            channel = self.channels.get(channel_name)
            if not channel:
                continue
            if not channel.can_deliver(notification.recipient):
                logger.info(
                    "notification_channel_skipped",
                    notification_id=notification.id,
                    channel=channel_name,
                )
                continue

            result = channel.deliver(
                notification.recipient,
                notification.rendered_text,
                context=notification.context,
            )
            NotificationDeliveryAttempt.objects.create(
                notification=notification,
                channel=channel_name,
                succeeded=result["succeeded"],
                error_message=result.get("error") or "",
                response_payload=result.get("response") or {},
            )
            notification_delivery_total.labels(
                channel=channel_name,
                status="success" if result["succeeded"] else "failed",
            ).inc()

            if result["succeeded"]:
                notification.status = Notification.Status.SENT
                notification.delivered_via = channel_name
                notification.sent_at = timezone.now()
                notification.save(update_fields=["status", "delivered_via", "sent_at"])
                logger.info(
                    "notification_delivered",
                    notification_id=notification.id,
                    channel=channel_name,
                )
                return True

            logger.warning(
                "notification_delivery_failed",
                notification_id=notification.id,
                channel=channel_name,
                error=result.get("error"),
            )

        notification.status = Notification.Status.FAILED
        notification.save(update_fields=["status"])
        notification_all_channels_failed_total.inc()
        logger.error("notification_all_channels_failed", notification_id=notification.id)
        return False


notification_dispatcher = NotificationDispatcher()
