from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.notifications.channels import BaseChannel
from apps.notifications.models import (
    Notification,
    NotificationDeliveryAttempt,
    NotificationTemplate,
)
from apps.notifications.services import NotificationDispatcher
from shared.metrics import notification_all_channels_failed_total, notification_delivery_total


class FakeChannel(BaseChannel):
    def __init__(self, name: str, *, can_deliver: bool = True, succeeds: bool = True):
        self.name = name
        self._can_deliver = can_deliver
        self._succeeds = succeeds

    def can_deliver(self, recipient) -> bool:
        return self._can_deliver

    def deliver(self, recipient, text: str, *, context: dict | None = None):
        return {
            "succeeded": self._succeeds,
            "error": None if self._succeeds else f"{self.name}_failed",
            "response": {"channel": self.name},
        }


class NotificationDispatcherTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="recipient")
        self.template = NotificationTemplate.objects.create(
            name="test",
            text="Hello {name}",
        )

    def make_notification(self):
        return Notification.objects.create(
            template=self.template,
            recipient=self.user,
            rendered_text="Hello recipient",
            context={"name": "recipient"},
        )

    def test_success_marks_notification_sent(self):
        notification = self.make_notification()
        dispatcher = NotificationDispatcher([FakeChannel("telegram")])
        before = notification_delivery_total.labels(channel="telegram", status="success")._value.get()

        assert dispatcher.dispatch(notification, ("telegram",)) is True

        notification.refresh_from_db()
        assert notification.status == Notification.Status.SENT
        assert notification.delivered_via == "telegram"
        assert notification.attempts.count() == 1
        after = notification_delivery_total.labels(channel="telegram", status="success")._value.get()
        assert after == before + 1

    def test_fallback_to_next_channel_after_failure(self):
        notification = self.make_notification()
        dispatcher = NotificationDispatcher([
            FakeChannel("telegram", succeeds=False),
            FakeChannel("max", succeeds=True),
        ])
        telegram_failed_before = notification_delivery_total.labels(
            channel="telegram",
            status="failed",
        )._value.get()
        max_success_before = notification_delivery_total.labels(channel="max", status="success")._value.get()

        assert dispatcher.dispatch(notification, ("telegram", "max")) is True

        notification.refresh_from_db()
        assert notification.status == Notification.Status.SENT
        assert notification.delivered_via == "max"
        assert list(notification.attempts.values_list("channel", "succeeded")) == [
            ("telegram", False),
            ("max", True),
        ]
        assert (
            notification_delivery_total.labels(channel="telegram", status="failed")._value.get()
            == telegram_failed_before + 1
        )
        assert (
            notification_delivery_total.labels(channel="max", status="success")._value.get()
            == max_success_before + 1
        )

    def test_skip_channel_when_can_deliver_false(self):
        notification = self.make_notification()
        dispatcher = NotificationDispatcher([
            FakeChannel("telegram", can_deliver=False),
            FakeChannel("email", succeeds=True),
        ])

        assert dispatcher.dispatch(notification, ("telegram", "email")) is True

        notification.refresh_from_db()
        assert notification.delivered_via == "email"
        assert list(notification.attempts.values_list("channel", flat=True)) == ["email"]

    def test_all_channels_fail_marks_notification_failed(self):
        notification = self.make_notification()
        dispatcher = NotificationDispatcher([
            FakeChannel("telegram", succeeds=False),
            FakeChannel("max", succeeds=False),
        ])
        before = notification_all_channels_failed_total._value.get()

        assert dispatcher.dispatch(notification, ("telegram", "max")) is False

        notification.refresh_from_db()
        assert notification.status == Notification.Status.FAILED
        assert NotificationDeliveryAttempt.objects.filter(notification=notification).count() == 2
        assert notification_all_channels_failed_total._value.get() == before + 1

    def test_missing_channel_is_ignored(self):
        notification = self.make_notification()
        dispatcher = NotificationDispatcher([FakeChannel("email", succeeds=True)])

        assert dispatcher.dispatch(notification, ("telegram", "email")) is True

        notification.refresh_from_db()
        assert notification.delivered_via == "email"
        assert notification.attempts.count() == 1
