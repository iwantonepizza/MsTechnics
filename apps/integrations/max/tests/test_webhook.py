import json
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.integrations.max.views import max_webhook


class MaxWebhookTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(MAX_WEBHOOK_SECRET="secret")
    def test_rejects_invalid_secret(self):
        request = self.factory.post(
            "/api/v1/integrations/max/webhook",
            data=json.dumps({"update_type": "message_created"}),
            content_type="application/json",
            HTTP_X_MAX_SECRET="wrong",
        )

        response = max_webhook(request)

        assert response.status_code == 403

    @override_settings(MAX_WEBHOOK_SECRET="secret")
    def test_start_message_dispatches_binding(self):
        payload = {
            "update_type": "message_created",
            "message": {"text": "/start ivan", "user": {"user_id": "chat-1"}},
        }
        request = self.factory.post(
            "/api/v1/integrations/max/webhook",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_MAX_SECRET="secret",
        )

        with patch("apps.integrations.max.views._bind_user") as bind_user:
            response = max_webhook(request)

        assert response.status_code == 200
        bind_user.assert_called_once_with(username="ivan", chat_id="chat-1")

    @override_settings(MAX_WEBHOOK_SECRET="")
    def test_callback_dispatches_application_done(self):
        payload = {
            "update_type": "message_callback",
            "callback": {
                "payload": "application_done:42",
                "user": {"user_id": "chat-1"},
            },
        }
        request = self.factory.post(
            "/api/v1/integrations/max/webhook",
            data=json.dumps(payload),
            content_type="application/json",
        )
        user = object()

        with (
            patch("apps.integrations.max.views._find_bound_user", return_value=user),
            patch("apps.integrations.max.views._mark_application_done") as mark_done,
        ):
            response = max_webhook(request)

        assert response.status_code == 200
        mark_done.assert_called_once_with(42, user)
