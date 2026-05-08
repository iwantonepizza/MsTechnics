from __future__ import annotations

import httpx
from django.conf import settings

from .base import BaseChannel, DeliveryResult


class MaxChannel(BaseChannel):
    name = "max"

    def can_deliver(self, recipient) -> bool:
        return bool(settings.MAX_BOT_TOKEN and _get_chat_id(recipient))

    def deliver(self, recipient, text: str, *, context: dict | None = None) -> DeliveryResult:
        if not settings.MAX_BOT_TOKEN:
            return {"succeeded": False, "error": "MAX_BOT_TOKEN is not set", "response": {}}

        chat_id = _get_chat_id(recipient)
        if not chat_id:
            return {"succeeded": False, "error": "recipient has no MAX chat id", "response": {}}

        message_payload = {
            "chat_id": chat_id,
            "text": text,
        }
        actions = (context or {}).get("actions")
        if actions:
            message_payload["reply_markup"] = {
                "inline_keyboard": [
                    [
                        {"text": action["label"], "callback_data": action["callback"]}
                        for action in actions
                    ]
                ]
            }

        try:
            with httpx.Client(timeout=settings.MAX_TIMEOUT_SEC) as client:
                response = client.post(
                    f"{settings.MAX_API_BASE.rstrip('/')}/messages",
                    params={"access_token": settings.MAX_BOT_TOKEN},
                    json=message_payload,
                )
            payload = _safe_json(response)
            if response.status_code in (200, 201):
                return {"succeeded": True, "error": None, "response": payload}
            return {
                "succeeded": False,
                "error": payload.get("message") or payload.get("error") or f"HTTP {response.status_code}",
                "response": payload,
            }
        except httpx.TimeoutException:
            return {"succeeded": False, "error": "timeout", "response": {}}
        except httpx.HTTPError as exc:
            return {"succeeded": False, "error": str(exc), "response": {}}


def _get_chat_id(recipient):
    return getattr(recipient, "max_chat_id", None) or getattr(recipient, "max_id", None)


def _safe_json(response: httpx.Response) -> dict:
    try:
        data = response.json()
        return data if isinstance(data, dict) else {"data": data}
    except ValueError:
        return {"text": response.text[:500]}
