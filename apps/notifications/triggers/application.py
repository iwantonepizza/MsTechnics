from __future__ import annotations

from django.db.models import Q

from apps.core.users.models import MsUser
from apps.notifications.triggers.utils import create_and_dispatch_notification


def notify_application_created(application) -> None:
    city = getattr(application.display, "city", None)
    context = _application_context(application, comment=(application.comment_monitoring or "")[:200])
    for user in _department_recipients("control", city):
        create_and_dispatch_notification(
            template_name="application_created",
            recipient=user,
            context=context,
            target=application,
        )


def notify_application_assigned(application) -> None:
    user = _executor_user(application.executor)
    if not user:
        return
    context = _application_context(
        application,
        comment=(application.comment_control_send or application.comment_monitoring or "")[:200],
    )
    create_and_dispatch_notification(
        template_name="application_assigned_to_executor",
        recipient=user,
        context=context,
        target=application,
    )


def notify_application_completed(application) -> None:
    city = getattr(application.display, "city", None)
    recipients = list(_department_recipients("control", city))
    creator = _creator_user(application)
    if creator and creator not in recipients:
        recipients.append(creator)

    context = _application_context(
        application,
        executor_name=str(application.executor) if application.executor else "Не назначен",
    )
    for user in recipients:
        create_and_dispatch_notification(
            template_name="application_completed",
            recipient=user,
            context=context,
            target=application,
        )


def _department_recipients(permission: str, city):
    users = MsUser.objects.filter(permission__in=[permission, "admin", "all"])
    if city:
        users = users.filter(Q(permission__in=["admin", "all"]) | Q(allowed_city=city))
    return users.distinct()


def _executor_user(executor):
    telegram_id = getattr(executor, "telegram_id", None)
    if not telegram_id:
        return None
    return MsUser.objects.filter(telegram_id=telegram_id).first()


def _creator_user(application):
    username = getattr(application, "user_monitoring", None)
    if not username:
        return None
    return MsUser.objects.filter(username=username).first()


def _application_context(application, **extra):
    context = {
        "application_id": application.id,
        "display_description": getattr(application.display, "description", None)
        or getattr(application.display, "slug", ""),
        "cell_position": getattr(application.cell, "position", "-"),
        "comment": "",
        "executor_name": "",
    }
    context.update(extra)
    return context
