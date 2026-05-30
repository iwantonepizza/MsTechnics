# ruff: noqa: RUF001, RUF002
"""
apps/directory/panels/services.py — сервис перемещения панелей.

T-2-041: закрывает задачу владельца #8.
Заменяет разрозненную логику из zip/views.py и main/Db/orm_query.py.

Правило: нельзя переместить панель с активной заявкой.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from django.db import transaction

from apps.activity.services import activity_logger
from shared.exceptions import PanelHasActiveApplication

if TYPE_CHECKING:
    from apps.core.references.models import Condition
    from apps.core.users.models import MsUser
    from apps.directory.displays.models import Cell
    from apps.directory.panels.models import Panel
    from apps.workflow.applications.models import Application

logger = structlog.get_logger(__name__)

# Статусы, означающие активную (незакрытую) заявку
ACTIVE_APPLICATION_STATUSES = frozenset(
    {
        "sent_to_control",
        "apply_in_control",
        "sent_to_service",
        "work_in_service",
        "done",
        "unable",
    }
)


class PanelMover:
    """
    Сервис перемещения панели между отделами.

    Использование:
        panel_mover.move(
            panel=panel,
            to_department="service",
            actor=request.user,
            comment="Отправлена на ремонт",
        )
    """

    def move(
        self,
        *,
        panel: Panel,
        to_department: str,
        actor: MsUser,
        comment: str = "",
    ) -> Panel:
        """
        Переместить панель в указанный отдел.

        Args:
            panel: экземпляр Panel
            to_department: имя целевого отдела (Department.name)
            actor: пользователь, выполняющий перемещение
            comment: причина/комментарий

        Raises:
            PanelHasActiveApplication: если у панели есть активная заявка
            DomainError: если отдел не найден
        """
        from apps.core.references.models import Department
        from apps.workflow.applications.models import Application

        # Проверяем активную заявку
        has_active = Application.objects.filter(
            panel=panel,
            status__name__in=ACTIVE_APPLICATION_STATUSES,
        ).exists()

        if has_active:
            raise PanelHasActiveApplication(
                f"Панель {panel.name} имеет активную заявку. "
                f"Завершите или архивируйте заявку перед перемещением.",
                panel=panel.name,
            )

        department = Department.objects.filter(name=to_department).first()
        if not department:
            from shared.exceptions import ObjectNotFound

            raise ObjectNotFound(f"Отдел '{to_department}' не найден.")

        from_department = panel.department.name if panel.department else "unknown"

        with transaction.atomic():
            panel.department = department
            panel.save(update_fields=["department"])

            # Пишем в ActivityLog
            activity_logger.log(
                actor=actor,
                target=panel,
                event_type="panel_move",
                description=f"Панель {panel.name}: {from_department} → {to_department}",
                comment=comment or "",
                payload={
                    "from_department": from_department,
                    "to_department": to_department,
                },
            )

        logger.info(
            "panel_moved",
            panel=panel.name,
            from_department=from_department,
            to_department=to_department,
            actor=str(actor),
        )
        return panel

    def replace_in_cell(
        self,
        *,
        cell: Cell,
        new_panel: Panel,
        actor: MsUser,
        comment: str = "",
    ) -> Panel:
        """
        Заменить панель в ячейке экрана.
        Старая панель уходит в сервис, новая — занимает её место.

        Args:
            cell: экземпляр Cell
            new_panel: новая Panel (должна быть в zip)
            actor: пользователь
            comment: комментарий

        Raises:
            PanelHasActiveApplication: если новая панель имеет активную заявку
        """
        from apps.core.references.models import Department
        from apps.workflow.applications.models import Application

        # Проверяем активную заявку на новой панели
        if Application.objects.filter(
            panel=new_panel,
            status__name__in=ACTIVE_APPLICATION_STATUSES,
        ).exists():
            raise PanelHasActiveApplication(
                f"Новая панель {new_panel.name} имеет активную заявку.",
                panel=new_panel.name,
            )

        old_panel = cell.panel

        with transaction.atomic():
            # Старая панель → сервис
            if old_panel:
                service_dept = Department.objects.filter(name="service").first()
                if service_dept:
                    old_panel.department = service_dept
                    old_panel.save(update_fields=["department"])

            # Новая панель → в экран
            monitor_dept = Department.objects.filter(name="monitor").first()
            if monitor_dept:
                new_panel.department = monitor_dept
            new_panel.save(update_fields=["department"])

            cell.panel = new_panel
            cell.save(update_fields=["panel"])

            activity_logger.log(
                actor=actor,
                target=cell.display,
                event_type="display_panel_replace",
                description=(
                    f"Ячейка {cell.position}: "
                    f"{old_panel.name if old_panel else '—'} → {new_panel.name}"
                ),
                comment=comment or "",
                payload={
                    "cell_position": cell.position,
                    "old_panel": old_panel.name if old_panel else None,
                    "new_panel": new_panel.name,
                },
            )

        logger.info(
            "panel_replaced_in_cell",
            cell=str(cell),
            old_panel=old_panel.name if old_panel else None,
            new_panel=new_panel.name,
        )
        return new_panel

    def change_condition(
        self,
        *,
        panel,
        new_condition,
        actor,
        comment: str = "",
    ):
        """Сменить состояние панели + записать в ActivityLog."""
        from apps.activity.services import activity_logger

        old_condition = panel.condition.name if panel.condition else "—"
        panel.condition = new_condition
        panel.save(update_fields=["condition"])
        activity_logger.log(
            actor=actor,
            target=panel,
            event_type="panel.condition_changed",
            description=f"Панель {panel.name}: {old_condition} → {new_condition.name}",
            comment=comment or "",
            payload={"from_condition": old_condition, "to_condition": new_condition.name},
        )
        return panel

    def move_to_cell(self, *, panel, cell, actor, comment: str = ""):
        """Поместить панель в конкретную ячейку."""
        return self.replace_in_cell(cell=cell, new_panel=panel, actor=actor, comment=comment)

    def remove_from_cell(
        self,
        *,
        panel: Panel,
        actor: MsUser,
        new_condition: Condition | None = None,
        comment: str = "",
        application: Application | None = None,
    ) -> Panel:
        """Снять панель с ячейки, при необходимости изменив её состояние."""
        from apps.core.references.models import Department
        from shared.exceptions import ObjectNotFound

        cell = panel.cell.select_related("display").first()
        if cell is None:
            raise ObjectNotFound(
                f"Панель {panel.name} не установлена в ячейку.",
                code="panel_not_installed",
            )

        service_department = Department.objects.filter(name="service").first()
        if service_department is None:
            raise ObjectNotFound("Отдел 'service' не найден.")

        with transaction.atomic():
            cell.panel = None
            cell.save(update_fields=["panel"])

            panel.department = service_department
            update_fields = ["department"]
            if new_condition is not None:
                panel.condition = new_condition
                update_fields.append("condition")
            panel.save(update_fields=update_fields)

            activity_logger.log(
                actor=actor,
                target=panel,
                event_type="panel.removed",
                description=(
                    f"Панель {panel.name} снята с {cell.position} " f"экрана {cell.display.name}"
                ),
                comment=comment or "",
                payload={
                    "from_cell_id": cell.id,
                    "display_id": cell.display_id,
                    "new_condition": new_condition.name if new_condition else None,
                    "via_application_id": application.id if application else None,
                },
            )

        logger.info(
            "panel_removed_from_cell",
            panel=panel.name,
            cell_id=cell.id,
            display=cell.display.name,
            actor=str(actor),
            via_application_id=application.id if application else None,
        )
        return panel


# Глобальный синглтон
panel_mover = PanelMover()


def delete_panel(*, panel: Panel, actor: MsUser) -> None:
    """Delete a panel together with non-active historical data in one transaction."""
    from django.contrib.contenttypes.models import ContentType

    from apps.activity.models import ActivityLog
    from apps.workflow.applications.models import Application, ApplicationHistoryReport
    from main_menu.models import PanelHistoryReport

    active_application = panel.active_application
    if active_application is not None:
        raise PanelHasActiveApplication(
            f"У панели {panel.name} есть активная заявка #{active_application.id}. "
            "Сначала закройте заявку.",
            panel=panel.name,
            application_id=active_application.id,
        )

    panel_id = panel.id
    panel_name = panel.name
    display_name = panel.display.name if panel.display else None

    installed_cell = panel.cell.select_related("display").first()
    installed_cell_id = installed_cell.id if installed_cell else None
    installed_cell_position = installed_cell.position if installed_cell else None

    related_application_ids = list(
        Application.objects.filter(panel=panel).values_list("id", flat=True)
    )
    related_application_ids_as_str = [
        str(application_id) for application_id in related_application_ids
    ]

    panel_content_type = ContentType.objects.get_for_model(panel.__class__)
    application_content_type = ContentType.objects.get_for_model(Application)

    with transaction.atomic():
        if installed_cell is not None:
            installed_cell.panel = None
            installed_cell.save(update_fields=["panel"])

        if related_application_ids:
            ActivityLog.objects.filter(
                target_type=application_content_type,
                target_id__in=related_application_ids,
            ).delete()
            ApplicationHistoryReport.objects.filter(
                application_id__in=related_application_ids_as_str
            ).delete()
            Application.objects.filter(id__in=related_application_ids).delete()
            ApplicationHistoryReport.objects.filter(
                application_id__in=related_application_ids_as_str
            ).delete()

        ActivityLog.objects.filter(target_type=panel_content_type, target_id=panel_id).delete()
        PanelHistoryReport.objects.filter(panel_id=panel_name).delete()

        panel.delete()

        activity_logger.log(
            event_type="panel.deleted",
            actor=actor,
            description=f"Удалена панель {panel_name}",
            payload={
                "panel_id": panel_id,
                "panel_name": panel_name,
                "display_name": display_name,
                "installed_cell_id": installed_cell_id,
                "installed_cell_position": installed_cell_position,
                "deleted_application_ids": related_application_ids,
            },
        )

    logger.info(
        "panel_deleted",
        panel_id=panel_id,
        panel=panel_name,
        actor=str(actor),
        related_application_ids=related_application_ids,
    )
