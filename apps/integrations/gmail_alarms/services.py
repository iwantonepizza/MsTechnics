from __future__ import annotations

import base64
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import AlarmEvent
from .parsers import AlarmRecord, AlarmType, parse_alarm_email


@dataclass(frozen=True)
class GmailAlarmMessage:
    id: str
    subject: str
    body: str


def ingest_alarm_email(*, message_id: str, subject: str, body: str) -> list[AlarmEvent]:
    events = []
    for record in parse_alarm_email(subject, body):
        events.append(process_alarm_record(record, gmail_message_id=message_id))
    return events


def process_alarm_record(record: AlarmRecord, *, gmail_message_id: str = "") -> AlarmEvent:
    from apps.directory.displays.models import Cell, Display

    display = Display.objects.filter(vnnox_device_id=record.device_id).first()
    cell = None
    panel = None
    if display and display.cols:
        row = ((record.receiving_card_no - 1) // display.cols) + 1
        col = ((record.receiving_card_no - 1) % display.cols) + 1
        cell = Cell.objects.filter(display=display, row=row, col=col).select_related("panel").first()
        panel = cell.panel if cell else None

    with transaction.atomic():
        event, _ = AlarmEvent.objects.get_or_create(
            gmail_message_id=gmail_message_id,
            type=record.type.value,
            device_id=record.device_id,
            receiving_card_no=record.receiving_card_no,
            occurred_at=record.timestamp,
            defaults={
                "display": display,
                "cell": cell,
                "panel": panel,
                "screen_name_raw": record.screen_name,
                "raw_position": record.raw_position,
                "raw_email_subject": record.raw_email_subject,
            },
        )
        if record.type == AlarmType.RECOVERY and display:
            _resolve_open_faulty(event)
    return event


def pull_unread_vnnox_messages(query: str = "from:service@alimail.vnnox.com is:unread") -> Iterable[GmailAlarmMessage]:
    service = build_gmail_service()
    response = service.users().messages().list(userId="me", q=query, includeSpamTrash=False).execute()
    for item in response.get("messages", []):
        message = service.users().messages().get(userId="me", id=item["id"], format="full").execute()
        yield GmailAlarmMessage(
            id=item["id"],
            subject=_header(message, "Subject"),
            body=_message_body(message.get("payload", {})),
        )


def mark_message_as_read(message_id: str) -> None:
    service = build_gmail_service()
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()


def gmail_client_secret_file() -> Path:
    client_secret_file = Path(settings.GOOGLE_CREDENTIALS_FILE)
    if not client_secret_file.is_absolute():
        client_secret_file = settings.BASE_DIR / client_secret_file
    return client_secret_file


def gmail_token_file() -> Path:
    return settings.BASE_DIR / "Config" / "token.pickle"


def check_gmail_oauth(
    query: str = "from:service@alimail.vnnox.com is:unread",
    *,
    max_results: int = 1,
) -> dict[str, object]:
    client_secret_file = gmail_client_secret_file()
    token_file = gmail_token_file()
    if not client_secret_file.exists():
        raise FileNotFoundError(f"Google client secret file not found: {client_secret_file}")
    if not token_file.exists():
        raise FileNotFoundError(f"Gmail token file not found: {token_file}")

    service = build_gmail_service()
    response = service.users().messages().list(
        userId="me",
        q=query,
        includeSpamTrash=False,
        maxResults=max(1, max_results),
    ).execute()
    messages = response.get("messages", [])

    return {
        "ok": True,
        "query": query,
        "client_secret_file": str(client_secret_file),
        "token_file": str(token_file),
        "result_size_estimate": int(response.get("resultSizeEstimate", 0)),
        "message_ids": [item["id"] for item in messages[:max_results] if "id" in item],
    }


def _resolve_open_faulty(recovery_event: AlarmEvent) -> None:
    faulty = (
        AlarmEvent.objects.filter(
            display=recovery_event.display,
            receiving_card_no=recovery_event.receiving_card_no,
            type=AlarmEvent.Type.FAULTY,
            resolved_at__isnull=True,
        )
        .exclude(id=recovery_event.id)
        .order_by("-occurred_at")
        .first()
    )
    if not faulty:
        return

    faulty.resolved_at = timezone.now()
    faulty.resolved_by_alarm = recovery_event
    faulty.save(update_fields=["resolved_at", "resolved_by_alarm"])


def build_gmail_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token_file = gmail_token_file()
    with open(token_file, encoding="utf-8") as token:
        credentials_data = json.load(token)
    if isinstance(credentials_data, str):
        credentials_data = json.loads(credentials_data)

    credentials = Credentials.from_authorized_user_info(credentials_data, settings.SCOPES)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        with open(token_file, "w", encoding="utf-8") as token:
            json.dump(json.loads(credentials.to_json()), token)

    return build("gmail", "v1", credentials=credentials)


def _header(message: dict, name: str) -> str:
    headers = message.get("payload", {}).get("headers", [])
    return next((item["value"] for item in headers if item.get("name") == name), "")


def _message_body(payload: dict) -> str:
    if payload.get("body", {}).get("data"):
        return _decode_body(payload["body"]["data"])
    for part in payload.get("parts", []):
        if part.get("mimeType") in ("text/html", "text/plain") and part.get("body", {}).get("data"):
            return _decode_body(part["body"]["data"])
    return ""


def _decode_body(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8")
