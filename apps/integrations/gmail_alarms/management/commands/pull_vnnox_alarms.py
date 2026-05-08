import structlog
from django.core.management.base import BaseCommand

from apps.integrations.gmail_alarms.services import (
    ingest_alarm_email,
    mark_message_as_read,
    pull_unread_vnnox_messages,
)

logger = structlog.get_logger(__name__)


class Command(BaseCommand):
    help = "Pull unread VNNOX emails from Gmail and create AlarmEvent rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--query",
            default="from:service@alimail.vnnox.com is:unread",
            help="Gmail search query.",
        )
        parser.add_argument(
            "--no-mark-read",
            action="store_true",
            help="Do not remove UNREAD label after successful processing.",
        )

    def handle(self, *args, **options):
        total_messages = 0
        total_events = 0
        for message in pull_unread_vnnox_messages(query=options["query"]):
            events = ingest_alarm_email(
                message_id=message.id,
                subject=message.subject,
                body=message.body,
            )
            total_messages += 1
            total_events += len(events)
            if events and not options["no_mark_read"]:
                mark_message_as_read(message.id)

        logger.info("vnnox_alarm_pull_finished", messages=total_messages, events=total_events)
        self.stdout.write(f"Processed {total_messages} messages, created/found {total_events} events")
