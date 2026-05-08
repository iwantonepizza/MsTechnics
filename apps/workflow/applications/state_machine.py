"""
apps/workflow/applications/state_machine.py

T-2-040: декларативный FSM заявки.
Заменяет 150-строчную функцию apply_application() с 7 ветками if/elif.

Принцип:
  - Каждый переход — объект Transition
  - ApplicationStateMachine.transition() — единственная точка входа
  - Права, валидация, создание событий, лог — всё здесь
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import structlog

from apps.workflow.applications.exceptions import InvalidTransition, TransitionPermissionDenied

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class Transition:
    """Описание одного допустимого перехода FSM."""

    from_status: str        # имя статуса-источника
    to_status: str          # имя статуса-назначения
    stage: str              # имя этапа → ApplicationEvent.stage
    allowed_roles: tuple[str, ...]   # кортеж permission-строк

    # Хуки — вызываются ПОСЛЕ сохранения нового статуса
    on_transition: list[Callable] = field(default_factory=list)

    # Нужен ли файл для этого перехода (не обязателен, но желателен)
    file_required: bool = False


# ─── Хуки ────────────────────────────────────────────────────────────────────

def _set_panel_condition_error(application, **_kwargs):
    """При принятии в контроль — панель переходит в состояние error."""
    from apps.core.references.models import Condition
    try:
        application.panel.condition = Condition.objects.get(name="error")
        application.panel.save(update_fields=["condition"])
    except Condition.DoesNotExist:
        logger.warning("condition_error_not_found", application_id=application.id)


def _set_panel_condition_work(application, **_kwargs):
    """При завершении ремонта — панель возвращается в work."""
    from apps.core.references.models import Condition
    try:
        application.panel.condition = Condition.objects.get(name="work")
        application.panel.save(update_fields=["condition"])
    except Condition.DoesNotExist:
        logger.warning("condition_work_not_found", application_id=application.id)


def _set_panel_status_default(application, **_kwargs):
    """Compat no-op: application_status панели теперь вычисляется из активной заявки."""
    return None


def _sync_panel_application_status(application, **_kwargs):
    """Compat no-op: application_status панели теперь вычисляется из активной заявки."""
    return None


# ─── Таблица переходов ────────────────────────────────────────────────────────

TRANSITIONS: list[Transition] = [
    Transition(
        from_status="sent_to_control",
        to_status="apply_in_control",
        stage="control_apply",
        allowed_roles=("control", "all", "admin"),
        on_transition=[_set_panel_condition_error, _sync_panel_application_status],
    ),
    Transition(
        from_status="apply_in_control",
        to_status="sent_to_service",
        stage="control_send",
        allowed_roles=("control", "all", "admin"),
        on_transition=[_sync_panel_application_status],
    ),
    Transition(
        from_status="sent_to_service",
        to_status="work_in_service",
        stage="service_apply",
        allowed_roles=("service", "all", "admin"),
        on_transition=[_sync_panel_application_status],
    ),
    Transition(
        from_status="work_in_service",
        to_status="done",
        stage="service_complete",
        allowed_roles=("service", "all", "admin"),
        on_transition=[_set_panel_condition_work, _sync_panel_application_status],
    ),
    Transition(
        from_status="work_in_service",
        to_status="unable",
        stage="service_unable",
        allowed_roles=("service", "all", "admin"),
        on_transition=[_sync_panel_application_status],
    ),
    Transition(
        from_status="done",
        to_status="archive_done",
        stage="archive_done",
        allowed_roles=("control", "all", "admin"),
        on_transition=[_set_panel_status_default],
    ),
    Transition(
        from_status="unable",
        to_status="archive_unable",
        stage="archive_unable",
        allowed_roles=("control", "all", "admin"),
        on_transition=[_set_panel_status_default],
    ),
]

# Быстрый lookup: (from_status, to_status) → Transition
_TRANSITION_MAP: dict[tuple[str, str], Transition] = {
    (t.from_status, t.to_status): t for t in TRANSITIONS
}


class ApplicationStateMachine:
    """
    Единственная точка входа для переходов состояний заявки.

    Использование:
        fsm = ApplicationStateMachine()
        fsm.transition(
            application=app,
            target_status="apply_in_control",
            actor=request.user,
            comment="Принял в работу",
        )
    """

    def get_transition(self, from_status: str, to_status: str) -> Transition:
        key = (from_status, to_status)
        transition = _TRANSITION_MAP.get(key)
        if not transition:
            raise InvalidTransition(
                f"Переход из '{from_status}' в '{to_status}' недопустим.",
                from_status=from_status,
                to_status=to_status,
            )
        return transition

    def available_transitions(self, application) -> list[Transition]:
        """Список допустимых переходов из текущего статуса."""
        current = application.status.name
        return [t for t in TRANSITIONS if t.from_status == current]

    def transition(
        self,
        *,
        application,
        target_status: str,
        actor,
        comment: str = "",
        file=None,
    ):
        """
        Выполнить переход заявки в target_status.

        Args:
            application: экземпляр Application
            target_status: имя целевого статуса
            actor: MsUser, выполняющий переход
            comment: текстовый комментарий
            file: прикреплённый файл (опционально)

        Raises:
            InvalidTransition: если переход недопустим
            TransitionPermissionDenied: если у actor нет прав
        """
        from django.utils import timezone
        from apps.workflow.applications.models import ApplicationStatus, ApplicationEvent
        from apps.activity.services import activity_logger

        current_status = application.status.name
        transition = self.get_transition(current_status, target_status)

        # Проверка прав
        if actor and actor.permission not in transition.allowed_roles:
            raise TransitionPermissionDenied(
                f"Роль '{actor.permission}' не может выполнить переход в '{target_status}'.",
                actor=actor.username,
                target_status=target_status,
            )

        now = timezone.now()

        # Обновляем статус заявки
        new_status = ApplicationStatus.objects.get(name=target_status)
        application.status = new_status
        application.last_update_date_time = now
        application.save(update_fields=["status", "last_update_date_time"])

        # Создаём событие
        actor_name = (
            f"{actor.first_name} {actor.last_name}".strip() if actor else "system"
        )
        ApplicationEvent.objects.create(
            application=application,
            stage=transition.stage,
            comment=comment or "",
            file=file,
            actor=actor,
            actor_name=actor_name,
            occurred_at=now,
        )

        # Запускаем хуки
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

        # Логируем в ActivityLog
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


    def available_transitions_from(self, state_name: str) -> list:
        """Все переходы из заданного состояния."""
        return [t for t in TRANSITIONS if t.from_status == state_name]

    def all_transitions(self) -> list:
        return list(TRANSITIONS)


# Глобальный синглтон
application_fsm = ApplicationStateMachine()
