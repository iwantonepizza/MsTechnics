from __future__ import annotations

import json
from typing import Any

import structlog
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.notifications.channels.max import MaxChannel

logger = structlog.get_logger(__name__)


@csrf_exempt
@require_POST
def max_webhook(request: HttpRequest) -> HttpResponse:
    if not _is_valid_secret(request):
        logger.warning("max_webhook_forbidden")
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("max_webhook_bad_payload")
        return JsonResponse({"ok": False, "error": "bad_payload"}, status=400)

    update_type = _update_type(payload)
    logger.info("max_webhook_received", update_type=update_type)

    if update_type == "message_callback":
        _handle_callback(payload)
    elif update_type == "message_created":
        _handle_user_message(payload)

    return JsonResponse({"ok": True})


def _is_valid_secret(request: HttpRequest) -> bool:
    expected = settings.MAX_WEBHOOK_SECRET
    if not expected:
        return True
    actual = request.headers.get("X-MAX-Secret") or request.headers.get("X-Max-Webhook-Secret")
    return actual == expected


def _update_type(payload: dict[str, Any]) -> str:
    return str(payload.get("update_type") or payload.get("type") or "")


def _handle_callback(payload: dict[str, Any]) -> None:
    callback = payload.get("callback") or payload.get("message_callback") or {}
    callback_data = str(callback.get("payload") or callback.get("callback_data") or "")
    if ":" not in callback_data:
        logger.warning("max_callback_ignored", reason="invalid_callback")
        return

    action, _, raw_ref = callback_data.partition(":")
    try:
        object_id = int(raw_ref)
    except ValueError:
        logger.warning("max_callback_ignored", reason="invalid_id", action=action)
        return

    chat_id = _callback_chat_id(callback)
    user = _find_bound_user(chat_id)
    if not user:
        logger.warning("max_callback_ignored", reason="user_not_bound", action=action)
        return

    if action == "application_done":
        _mark_application_done(object_id, user)
    else:
        logger.warning("max_callback_ignored", reason="unsupported_action", action=action)


def _handle_user_message(payload: dict[str, Any]) -> None:
    message = payload.get("message") or {}
    text = str(message.get("text") or "").strip()
    chat_id = _message_chat_id(message)
    if not chat_id:
        logger.warning("max_message_ignored", reason="missing_chat_id")
        return

    if text.startswith("/start "):
        username = text.removeprefix("/start ").strip()
        _bind_user(username=username, chat_id=chat_id)
    elif text == "/unbind":
        _unbind_user(chat_id=chat_id)
    elif text == "/start":
        _send_max_message(chat_id, "Используй: /start <твой_username>")


def _callback_chat_id(callback: dict[str, Any]) -> str:
    user = callback.get("user") or {}
    return str(user.get("user_id") or user.get("id") or callback.get("chat_id") or "")


def _message_chat_id(message: dict[str, Any]) -> str:
    user = message.get("user") or message.get("sender") or {}
    return str(user.get("user_id") or user.get("id") or message.get("chat_id") or "")


def _find_bound_user(chat_id: str):
    if not chat_id:
        return None
    from apps.core.users.models import MsUser

    return MsUser.objects.filter(max_id=chat_id).first()


def _bind_user(*, username: str, chat_id: str) -> None:
    from apps.core.users.models import MsUser

    user = MsUser.objects.filter(username=username).first()
    if not user:
        _send_max_message(chat_id, "Пользователь не найден")
        return

    existing = MsUser.objects.filter(max_id=chat_id).exclude(id=user.id).first()
    if existing:
        _send_max_message(chat_id, "Этот MAX-аккаунт уже привязан к другому пользователю")
        return

    user.max_id = chat_id
    user.save(update_fields=["max_id"])
    _send_max_message(chat_id, f"Привязка успешна. Привет, {user.username}!")


def _unbind_user(*, chat_id: str) -> None:
    user = _find_bound_user(chat_id)
    if not user:
        _send_max_message(chat_id, "Этот MAX-аккаунт не был привязан")
        return

    user.max_id = None
    user.save(update_fields=["max_id"])
    _send_max_message(chat_id, "MAX-аккаунт отвязан")


def _send_max_message(chat_id: str, text: str) -> None:
    recipient = type("MaxRecipient", (), {"max_id": chat_id})()
    result = MaxChannel().deliver(recipient, text)
    if not result["succeeded"]:
        logger.warning("max_webhook_reply_failed", error=result["error"])


def _mark_application_done(application_id: int, user) -> None:
    from apps.workflow.applications.models import Application
    from apps.workflow.applications.services import application_service

    application = Application.objects.filter(id=application_id).select_related("status").first()
    if not application:
        logger.warning("max_callback_application_not_found")
        return

    application_service.transition(
        application=application,
        target_status="done",
        actor=user,
        comment="Завершено из MAX",
    )
