"""
apps/workflow/applications/services.py — сервисный слой заявок.

T-2-040: заменяет application/utils.py.
Вся бизнес-логика здесь. Views вызывают только эти методы.

Compat: application/utils.py оставлен как shim для старых views.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from django.db import transaction
from django.utils import timezone

from apps.activity.services import activity_logger
from apps.workflow.applications.exceptions import ApplicationNotFound
from apps.workflow.applications.state_machine import application_fsm
from shared.exceptions import DomainError

if TYPE_CHECKING:
    from apps.core.users.models import MsUser
    from apps.workflow.applications.models import Application

logger = structlog.get_logger(__name__)


class ApplicationService:
    """Сервис управления жизненным циклом заявок."""

    @staticmethod
    def create(
        *,
        panel,
        comment: str,
        time_event,
        user: "MsUser",
        file=None,
    ) -> "Application":
        """
        Создать заявку на панель.

        Raises:
            DomainError: если панель не в подходящем состоянии или уже имеет заявку.
        """
        from apps.directory.displays.models import Cell
        from apps.workflow.applications.models import Application, ApplicationEvent, ApplicationStatus

        if panel.application_status and panel.application_status.name != "default":
            raise DomainError(
                f"Панель {panel.name} уже имеет активную заявку.",
                panel=panel.name,
                current_status=panel.application_status.name,
            )

        if panel.condition and panel.condition.name == "unrecoverable":
            raise DomainError(
                f"Панель {panel.name} в состоянии '{panel.condition.name}' — заявку создать нельзя.",
                panel=panel.name,
                condition=panel.condition.name,
            )

        cell = Cell.objects.filter(panel=panel).first()
        if not cell:
            raise DomainError(f"Панель {panel.name} не установлена ни в одну ячейку.")

        status = ApplicationStatus.objects.get(name="sent_to_control")

        with transaction.atomic():
            app = Application.objects.create(
                display=panel.display,
                panel=panel,
                cell=cell,
                status=status,
                comment_monitoring=comment,
                time_monitoring=time_event,
                last_update_date_time=time_event,
                file_monitoring=file,
                user_monitoring=user.full_name if hasattr(user, "full_name") else str(user),
            )

            ApplicationEvent.objects.create(
                application=app,
                stage="monitoring_create",
                comment=comment or "",
                file=file,
                actor=user,
                actor_name=getattr(user, "full_name", str(user)),
                occurred_at=time_event or timezone.now(),
            )

            activity_logger.log(
                actor=user,
                target=app,
                event_type="application_create",
                description=f"Создана заявка #{app.id} на панель {panel.name}",
                comment=comment or "",
                payload={"panel": panel.name, "display": panel.display.name if panel.display else None},
            )

        logger.info("application_created", application_id=app.id, panel=panel.name)
        try:
            from apps.notifications.triggers.application import notify_application_created

            notify_application_created(app)
        except Exception:
            logger.exception("application_created_notification_failed", application_id=app.id)
        return app

    @staticmethod
    def transition(
        *,
        application: "Application",
        target_status: str,
        actor: "MsUser",
        comment: str = "",
        file=None,
    ) -> "Application":
        """Выполнить переход заявки. Делегирует в ApplicationStateMachine."""
        app = application_fsm.transition(
            application=application,
            target_status=target_status,
            actor=actor,
            comment=comment,
            file=file,
        )
        if target_status == "done":
            try:
                from apps.notifications.triggers.application import notify_application_completed

                notify_application_completed(app)
            except Exception:
                logger.exception("application_completed_notification_failed", application_id=app.id)
        return app

    @staticmethod
    def delete(
        *,
        application: "Application",
        actor: "MsUser",
        comment: str = "",
    ) -> None:
        """
        Удалить заявку.
        Разрешено только из статуса 'sent_to_control'.
        """
        from apps.workflow.applications.models import ApplicationStatus

        allowed_statuses = ("sent_to_control",)
        if application.status.name not in allowed_statuses:
            raise DomainError(
                f"Удаление заявки #{application.id} невозможно из статуса '{application.status.name}'.",
                current_status=application.status.name,
            )

        panel = application.panel
        app_id = application.id

        with transaction.atomic():
            activity_logger.log(
                actor=actor,
                target=application,
                event_type="application_delete",
                description=f"Удалена заявка #{app_id}",
                comment=comment or "",
                payload={"panel": panel.name if panel else None},
            )

            application.delete()

        logger.info("application_deleted", application_id=app_id, actor=str(actor))

    @staticmethod
    def set_executor(
        *,
        application: "Application",
        executor,
        actor: "MsUser",
        comment: str = "",
    ) -> "Application":
        """Назначить/сменить исполнителя заявки."""
        from apps.workflow.applications.models import ApplicationEvent

        old_executor = application.executor
        application.executor = executor
        application.save(update_fields=["executor"])

        desc = (
            f"Исполнитель изменён: {old_executor} → {executor}"
            if old_executor
            else f"Назначен исполнитель: {executor}"
        )
        ApplicationEvent.objects.create(
            application=application,
            stage="monitoring_create",  # TODO: добавить stage executor_change
            comment=comment or desc,
            actor=actor,
            actor_name=getattr(actor, "full_name", str(actor)),
        )

        activity_logger.log(
            actor=actor,
            target=application,
            event_type="application_executor_change",
            description=desc,
            comment=comment or "",
        )
        try:
            from apps.notifications.triggers.application import notify_application_assigned

            notify_application_assigned(application)
        except Exception:
            logger.exception("application_assigned_notification_failed", application_id=application.id)
        return application

    @staticmethod
    def create_from_ids(
        *,
        display_id: int,
        panel_id: int,
        cell_id: int,
        comment: str,
        user,
        file=None,
    ):
        """Wrapper принимающий pk вместо объектов — для API views."""
        from apps.directory.panels.models import Panel
        panel = Panel.objects.get(id=panel_id)
        return ApplicationService.create(
            panel=panel, comment=comment,
            time_event=None, user=user, file=file,
        )


# Глобальный синглтон
application_service = ApplicationService()
