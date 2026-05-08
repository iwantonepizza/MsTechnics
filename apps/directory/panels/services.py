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
    from apps.core.users.models import MsUser
    from apps.directory.panels.models import Panel

logger = structlog.get_logger(__name__)

# Статусы, означающие активную (незакрытую) заявку
ACTIVE_APPLICATION_STATUSES = frozenset({
    "sent_to_control",
    "apply_in_control",
    "sent_to_service",
    "work_in_service",
    "done",
    "unable",
})


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
        panel: "Panel",
        to_department: str,
        actor: "MsUser",
        comment: str = "",
    ) -> "Panel":
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
        cell,
        new_panel: "Panel",
        actor: "MsUser",
        comment: str = "",
    ) -> "Panel":
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
            actor=actor, target=panel, event_type="panel.condition_changed",
            description=f"Панель {panel.name}: {old_condition} → {new_condition.name}",
            comment=comment or "",
            payload={"from_condition": old_condition, "to_condition": new_condition.name},
        )
        return panel

    def move_to_cell(self, *, panel, cell, actor, comment: str = ""):
        """Поместить панель в конкретную ячейку."""
        return self.replace_in_cell(cell=cell, new_panel=panel, actor=actor, comment=comment)

    def remove_from_cell(self, *, panel, actor, new_condition=None, comment: str = ""):
        """Снять панель с ячейки (поместить в null)."""
        from apps.activity.services import activity_logger
        from django.db import transaction
        with transaction.atomic():
            from apps.directory.displays.models import Cell
            try:
                cell = panel.cell
                display = cell.display
                cell.panel = None
                cell.save(update_fields=["panel"])
            except Exception:
                display = None
            if new_condition:
                panel.condition = new_condition
                panel.save(update_fields=["condition"])
            activity_logger.log(
                actor=actor, target=panel, event_type="panel.removed",
                description=f"Панель {panel.name} снята с ячейки",
                comment=comment or "",
            )
        return panel


# Глобальный синглтон
panel_mover = PanelMover()
