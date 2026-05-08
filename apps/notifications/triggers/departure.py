from __future__ import annotations

from apps.core.users.models import MsUser
from apps.notifications.triggers.utils import create_and_dispatch_notification


def notify_departure_assigned(departure, applications_count: int = 0) -> None:
    executor = getattr(departure, "executor", None)
    telegram_id = getattr(executor, "telegram_id", None)
    if not telegram_id:
        return

    user = MsUser.objects.filter(telegram_id=telegram_id).first()
    if not user:
        return

    context = {
        "departure_date": departure.time_start or departure.time_created or "",
        "description": departure.description or "",
        "applications_count": applications_count,
    }
    create_and_dispatch_notification(
        template_name="departure_assigned",
        recipient=user,
        context=context,
        target=departure,
    )
