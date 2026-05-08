"""Request-scoped logging and Sentry context."""
from __future__ import annotations

import uuid

from structlog.contextvars import bind_contextvars, clear_contextvars

try:
    import sentry_sdk
except ImportError:  # pragma: no cover - sentry-sdk is optional at import time
    sentry_sdk = None


REQUEST_ID_HEADER = "HTTP_X_REQUEST_ID"


class RequestContextMiddleware:
    """Bind request_id/user_id to structlog and Sentry without sending PII."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        clear_contextvars()
        request_id = request.META.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.request_id = request_id

        user = getattr(request, "user", None)
        user_id = getattr(user, "id", None) if getattr(user, "is_authenticated", False) else None

        bind_contextvars(request_id=request_id, user_id=user_id)
        if sentry_sdk is not None:
            sentry_sdk.set_tag("request_id", request_id)
            sentry_sdk.set_user({"id": str(user_id)} if user_id is not None else None)

        try:
            response = self.get_response(request)
            response["X-Request-ID"] = request_id
            return response
        finally:
            clear_contextvars()
