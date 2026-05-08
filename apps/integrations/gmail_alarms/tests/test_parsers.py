from apps.integrations.gmail_alarms.parsers import AlarmType, parse_alarm_email


FAULTY_BODY = """
Device：2YHA23816W3A10048571-00
Screen Alarm Time：(UTC+05:00) 2026-04-23 00:01:28
2026-04-23 00:01:28 | Receiving card abnormal | Faulty | Screen(No:1)-RC(No:13) | -
2026-04-23 00:01:28 | Receiving card abnormal | Faulty | Screen(No:1)-Receiving card(No:27) | -
"""

RECOVERY_BODY = """
<html><body>
<p>Device: 2YHA23816W3A10048571-00</p>
<p>Screen Recovery Time:(UTC+05:00) 2026-04-23 00:11:28</p>
<table><tr><td>2026-04-23 00:11:28</td><td>Receiving card</td><td>Recovered</td>
<td>Screen(No:1)-RC(No:13)</td></tr></table>
</body></html>
"""


def test_parse_faulty_alarm_extracts_unique_receiving_cards():
    records = parse_alarm_email("Faulty Alarm Notification: Колизей", FAULTY_BODY)

    assert [record.receiving_card_no for record in records] == [13, 27]
    assert {record.type for record in records} == {AlarmType.FAULTY}
    assert records[0].device_id == "2YHA23816W3A10048571-00"
    assert records[0].screen_name == "Колизей"
    assert records[0].timestamp.utcoffset().total_seconds() == 18_000


def test_parse_recovery_alarm_from_html_body():
    records = parse_alarm_email("Recovery Notification: Колизей", RECOVERY_BODY)

    assert len(records) == 1
    assert records[0].type == AlarmType.RECOVERY
    assert records[0].receiving_card_no == 13


def test_parse_unknown_subject_returns_empty_list():
    assert parse_alarm_email("Daily report", FAULTY_BODY) == []
