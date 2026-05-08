from __future__ import annotations

import httpx
import structlog
from django.conf import settings

from .base import BaseChannel, DeliveryResult

logger = structlog.get_logger(__name__)


class TelegramChannel(BaseChannel):
    name = "telegram"

    def can_deliver(self, recipient) -> bool:
        return bool(settings.TELEGRAM_BOT_TOKEN and getattr(recipient, "telegram_id", None))

    def deliver(self, recipient, text: str, *, context: dict | None = None) -> DeliveryResult:
        if not settings.TELEGRAM_BOT_TOKEN:
            return {"succeeded": False, "error": "TELEGRAM_BOT_TOKEN is not set", "response": {}}

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        client_kwargs = {"timeout": settings.TELEGRAM_TIMEOUT_SEC}
        if settings.TELEGRAM_PROXY_URL:
            client_kwargs["proxy"] = settings.TELEGRAM_PROXY_URL

        try:
            with httpx.Client(**client_kwargs) as client:
                response = client.post(
                    url,
                    json={
                        "chat_id": recipient.telegram_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                )
            payload = _safe_json(response)
            if response.status_code == 200:
                return {"succeeded": True, "error": None, "response": payload}
            error = payload.get("description") or f"HTTP {response.status_code}"
            return {"succeeded": False, "error": error, "response": payload}
        except httpx.TimeoutException:
            return {"succeeded": False, "error": "timeout", "response": {}}
        except httpx.ProxyError as exc:
            logger.warning("telegram_proxy_error", error=str(exc))
            return {"succeeded": False, "error": f"proxy: {exc}", "response": {}}
        except httpx.HTTPError as exc:
            return {"succeeded": False, "error": str(exc), "response": {}}


def _safe_json(response: httpx.Response) -> dict:
    try:
        data = response.json()
        return data if isinstance(data, dict) else {"data": data}
    except ValueError:
        return {"text": response.text[:500]}
