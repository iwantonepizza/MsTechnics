"""Application lifecycle state machine."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import structlog

from apps.core.users.permissions import has_role
from apps.workflow.applications.exceptions import InvalidTransition, TransitionPermissionDenied

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class Transition:
    """Description of one allowed application transition."""

    from_status: str
    to_status: str
    stage: str
    allowed_roles: tuple[str, ...]
    on_transition: list[Callable] = field(default_factory=list)
    file_required: bool = False


def _set_panel_condition_error(application, **_kwargs):
    """A newly accepted application marks the panel as problematic."""
    from apps.core.references.models import Condition

    try:
        application.panel.condition = Condition.objects.get(name="error")
        application.panel.save(update_fields=["condition"])
    except Condition.DoesNotExist:
        logger.warning("condition_error_not_found", application_id=application.id)


def _set_panel_condition_work(application, **_kwargs):
    """A completed repair restores the panel condition back to work."""
    from apps.core.references.models import Condition

    try:
        application.panel.condition = Condition.objects.get(name="work")
        application.panel.save(update_fields=["condition"])
    except Condition.DoesNotExist:
        logger.warning("condition_work_not_found", application_id=application.id)


TRANSITIONS: list[Transition] = [
    Transition(
        from_status="sent_to_control",
        to_status="apply_in_control",
        stage="control_apply",
        allowed_roles=("control", "admin"),
        on_transition=[_set_panel_condition_error],
    ),
    Transition(
        from_status="apply_in_control",
        to_status="sent_to_service",
        stage="control_send",
        allowed_roles=("control", "admin"),
    ),
    Transition(
        from_status="sent_to_service",
        to_status="work_in_service",
        stage="service_apply",
        allowed_roles=("service", "admin"),
    ),
    Transition(
        from_status="work_in_service",
        to_status="done",
        stage="service_complete",
        allowed_roles=("service", "admin"),
        on_transition=[_set_panel_condition_work],
    ),
    Transition(
        from_status="work_in_service",
        to_status="unable",
        stage="service_unable",
        allowed_roles=("service", "admin"),
    ),
    Transition(
        from_status="done",
        to_status="archive_done",
        stage="archive_done",
        allowed_roles=("control", "admin"),
    ),
    Transition(
        from_status="unable",
        to_status="archive_unable",
        stage="archive_unable",
        allowed_roles=("control", "admin"),
    ),
]

_TRANSITION_MAP: dict[tuple[str, str], Transition] = {
    (transition.from_status, transition.to_status): transition for transition in TRANSITIONS
}


class ApplicationStateMachine:
    """Single entry point for application status changes."""

    def get_transition(self, from_status: str, to_status: str) -> Transition:
        transition = _TRANSITION_MAP.get((from_status, to_status))
        if transition is None:
            raise InvalidTransition(
                f"Переход из '{from_status}' в '{to_status}' недопустим.",
                from_status=from_status,
                to_status=to_status,
            )
        return transition

    def available_transitions(self, application) -> list[Transition]:
        current = application.status.name
        return [transition for transition in TRANSITIONS if transition.from_status == current]

    def transition(
        self,
        *,
        application,
        target_status: str,
        actor,
        comment: str = "",
        file=None,
    ):
        from django.utils import timezone

        from apps.activity.services import activity_logger
        from apps.workflow.applications.models import ApplicationEvent, ApplicationStatus

        current_status = application.status.name
        transition = self.get_transition(current_status, target_status)

        if actor and not has_role(actor, *transition.allowed_roles):
            raise TransitionPermissionDenied(
                f"Пользователь '{actor.username}' не может выполнить переход в '{target_status}'.",
                actor=actor.username,
                target_status=target_status,
            )

        now = timezone.now()
        new_status = ApplicationStatus.objects.get(name=target_status)
        application.status = new_status
        application.last_update_date_time = now
        application.save(update_fields=["status", "last_update_date_time"])

        actor_name = f"{actor.first_name} {actor.last_name}".strip() if actor else "system"
        ApplicationEvent.objects.create(
            application=application,
            stage=transition.stage,
            comment=comment or "",
            file=file,
            actor=actor,
            actor_name=actor_name,
            occurred_at=now,
        )

        for hook in transition.on_transition:
            try:
                hook(application=application, actor=actor, comment=comment)
            except Exception:
                logger.exception(
                    "fsm_hook_failed",
                    hook=hook.__name__,
                    application_id=application.id,
                    transition=f"{current_status}->{target_status}",
                )

        activity_logger.log(
            actor=actor,
            target=application,
            event_type="application_transition",
            description=f"Заявка #{application.id}: {current_status} → {target_status}",
            comment=comment or "",
            payload={
                "from_status": current_status,
                "to_status": target_status,
                "stage": transition.stage,
            },
        )

        logger.info(
            "application_transition",
            application_id=application.id,
            from_status=current_status,
            to_status=target_status,
            actor=actor_name,
        )
        return application

    def available_transitions_from(self, state_name: str) -> list[Transition]:
        return [transition for transition in TRANSITIONS if transition.from_status == state_name]

    def all_transitions(self) -> list[Transition]:
        return list(TRANSITIONS)


application_fsm = ApplicationStateMachine()
