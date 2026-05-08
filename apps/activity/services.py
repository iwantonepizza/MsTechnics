"""
apps/activity/services.py — сервис логирования событий.

Использование:
    from apps.activity.services import activity_logger

    activity_logger.log(
        actor=request.user,
        target=panel,
        event_type="panel_move",
        description="Панель P-00042 перемещена в сервис",
        comment=comment,
        payload={"from_department": "zip", "to_department": "service"},
    )
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from apps.activity.models import ActivityLog

if TYPE_CHECKING:
    from django.db.models import Model
    from apps.core.users.models import MsUser

logger = structlog.get_logger(__name__)


class ActivityLogger:
    def log(
        self,
        *,
        event_type: str,
        target: "Model | None" = None,
        actor: "MsUser | None" = None,
        description: str = "",
        comment: str = "",
        payload: dict | None = None,
        ip_address: str | None = None,
    ) -> ActivityLog:
        from django.contrib.contenttypes.models import ContentType

        actor_name = ""
        if actor:
            actor_name = f"{actor.first_name} {actor.last_name}".strip() or actor.username

        ct = None
        target_id = None
        if target is not None:
            ct = ContentType.objects.get_for_model(target)
            target_id = target.pk

        entry = ActivityLog.objects.create(
            actor=actor,
            actor_name=actor_name,
            target_type=ct,
            target_id=target_id,
            event_type=event_type,
            description=description,
            comment=comment,
            payload=payload or {},
            ip_address=ip_address,
        )

        logger.info(
            "activity_logged",
            event_type=event_type,
            actor=actor_name,
            target=str(target) if target else None,
        )
        return entry


# Глобальный синглтон — импортируй и используй
activity_logger = ActivityLogger()
