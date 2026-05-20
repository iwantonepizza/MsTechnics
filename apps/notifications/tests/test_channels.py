from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
from django.test import SimpleTestCase, override_settings

from apps.notifications.channels.email import EmailChannel
from apps.notifications.channels.max import MaxChannel
from apps.notifications.channels.telegram import TelegramChannel


class TelegramChannelTests(SimpleTestCase):
    @override_settings(TELEGRAM_BOT_TOKEN="token", TELEGRAM_PROXY_URL="http://proxy", TELEGRAM_TIMEOUT_SEC=10)
    def test_deliver_uses_proxy_and_html_parse_mode(self):
        recipient = SimpleNamespace(telegram_id="123")
        response = httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

        with patch("apps.notifications.channels.telegram.httpx.Client") as client_cls:
            client = client_cls.return_value.__enter__.return_value
            client.post.return_value = response

            result = TelegramChannel().deliver(recipient, "<b>Hello</b>")

        assert result["succeeded"] is True
        client_cls.assert_called_once_with(timeout=10, proxy="http://proxy")
        client.post.assert_called_once()
        assert client.post.call_args.kwargs["json"]["parse_mode"] == "HTML"

    @override_settings(TELEGRAM_BOT_TOKEN="")
    def test_missing_token_returns_error_without_request(self):
        result = TelegramChannel().deliver(SimpleNamespace(telegram_id="123"), "Hello")

        assert result["succeeded"] is False
        assert result["error"] == "TELEGRAM_BOT_TOKEN is not set"


class MaxChannelTests(SimpleTestCase):
    @override_settings(MAX_BOT_TOKEN="token", MAX_API_BASE="https://platform-api.max.ru", MAX_TIMEOUT_SEC=7)
    def test_deliver_posts_to_platform_messages_endpoint(self):
        recipient = SimpleNamespace(max_id="chat-1")
        response = httpx.Response(201, json={"message": {"id": "msg-1"}})

        with patch("apps.notifications.channels.max.httpx.Client") as client_cls:
            client = client_cls.return_value.__enter__.return_value
            client.post.return_value = response

            result = MaxChannel().deliver(recipient, "Hello")

        assert result["succeeded"] is True
        client_cls.assert_called_once_with(timeout=7)
        client.post.assert_called_once_with(
            "https://platform-api.max.ru/messages",
            params={"access_token": "token"},
            json={"chat_id": "chat-1", "text": "Hello"},
        )

    @override_settings(MAX_BOT_TOKEN="token", MAX_API_BASE="https://platform-api.max.ru", MAX_TIMEOUT_SEC=7)
    def test_deliver_adds_inline_actions_from_context(self):
        recipient = SimpleNamespace(max_id="chat-1")
        response = httpx.Response(201, json={"message": {"id": "msg-1"}})

        with patch("apps.notifications.channels.max.httpx.Client") as client_cls:
            client = client_cls.return_value.__enter__.return_value
            client.post.return_value = response

            result = MaxChannel().deliver(
                recipient,
                "Hello",
                context={"actions": [{"label": "Готово", "callback": "application_done:42"}]},
            )

        assert result["succeeded"] is True
        assert client.post.call_args.kwargs["json"]["reply_markup"] == {
            "inline_keyboard": [[{"text": "Готово", "callback_data": "application_done:42"}]]
        }

    @override_settings(MAX_BOT_TOKEN="")
    def test_missing_token_returns_error_without_request(self):
        result = MaxChannel().deliver(SimpleNamespace(max_id="chat-1"), "Hello")

        assert result["succeeded"] is False
        assert result["error"] == "MAX_BOT_TOKEN is not set"


class EmailChannelTests(SimpleTestCase):
    @override_settings(DEFAULT_FROM_EMAIL="noreply@example.test")
    def test_deliver_uses_django_send_mail(self):
        recipient = SimpleNamespace(email="user@example.test")

        with patch("apps.notifications.channels.email.send_mail", Mock(return_value=1)) as send:
            result = EmailChannel().deliver(recipient, "Hello")

        assert result["succeeded"] is True
        send.assert_called_once_with(
            subject="[Суперсимметрия] Уведомление",
            message="Hello",
            from_email="noreply@example.test",
            recipient_list=["user@example.test"],
            fail_silently=False,
        )
