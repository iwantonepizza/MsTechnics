from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from bs4 import BeautifulSoup


class AlarmType(Enum):
    FAULTY = "faulty"
    RECOVERY = "recovery"


@dataclass(frozen=True)
class AlarmRecord:
    type: AlarmType
    device_id: str
    screen_name: str
    timestamp: datetime
    receiving_card_no: int
    raw_position: str
    raw_email_subject: str


SUBJECT_RE = re.compile(r"^(Faulty Alarm|Recovery) Notification:\s*(.+)$")
DEVICE_RE = re.compile(r"Device[：:]\s*([A-Za-z0-9-]+)")
TIME_RE = re.compile(
    r"Screen (?:Alarm|Recovery) Time[：:]\s*\((UTC[+-]\d{2}:\d{2})\)\s*"
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
)
RC_RE = re.compile(r"(?:Receiving card|RC)\(No:\s*(\d+)\)", re.IGNORECASE)


def parse_alarm_email(subject: str, body: str) -> list[AlarmRecord]:
    """Парсит письмо VNNOX в одну запись на каждую receiving card."""
    subject_match = SUBJECT_RE.match(subject.strip())
    if not subject_match:
        return []

    text = _html_to_text(body)
    device_match = DEVICE_RE.search(text)
    time_match = TIME_RE.search(text)
    if not device_match or not time_match:
        return []

    alarm_type = AlarmType.FAULTY if subject_match.group(1) == "Faulty Alarm" else AlarmType.RECOVERY
    timestamp = _parse_timestamp(time_match.group(1), time_match.group(2))
    raw_positions = _raw_positions_by_rc(text)

    return [
        AlarmRecord(
            type=alarm_type,
            device_id=device_match.group(1),
            screen_name=subject_match.group(2).strip(),
            timestamp=timestamp,
            receiving_card_no=number,
            raw_position=raw_positions[number],
            raw_email_subject=subject,
        )
        for number in sorted(raw_positions)
    ]


def _html_to_text(body: str) -> str:
    if "<" not in body or ">" not in body:
        return body
    return BeautifulSoup(body, "html.parser").get_text("\n")


def _parse_timestamp(tz_text: str, value: str) -> datetime:
    sign = 1 if "+" in tz_text else -1
    hours, minutes = (int(part) for part in tz_text.removeprefix("UTC").lstrip("+-").split(":"))
    tz = timezone(sign * timedelta(hours=hours, minutes=minutes))
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)


def _raw_positions_by_rc(text: str) -> dict[int, str]:
    positions: dict[int, str] = {}
    for line in text.splitlines():
        for match in RC_RE.finditer(line):
            number = int(match.group(1))
            positions[number] = line.strip() or f"RC(No:{number})"
    return positions
