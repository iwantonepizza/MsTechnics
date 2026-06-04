"""
apps/directory/displays/services.py — сервис создания экранов с layout.

T-2-027: выносит side-effects из Display.save() в явный сервис.
Display.save() становится стандартным Django-поведением.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog
from django.db import transaction

from apps.activity.services import activity_logger

if TYPE_CHECKING:
    from apps.core.users.models import MsUser
    from apps.directory.displays.models import Display

logger = structlog.get_logger(__name__)

DISPLAY_ASSET_FIELDS = {
    "schematic": "file",
    "project": "project_photo",
}


def stored_file_url(field_file) -> str | None:
    """Return a URL only when the referenced file is present in storage."""
    if not field_file or not getattr(field_file, "name", ""):
        return None
    try:
        if not field_file.storage.exists(field_file.name):
            return None
        return field_file.url
    except (NotImplementedError, OSError, ValueError):
        logger.warning("media_reference_check_failed", file_name=field_file.name)
        return None


@dataclass
class DisplayLayoutSpec:
    name: str
    city_name: str  # имя города (Cities.name) — legacy-связь через to_field
    rows: int
    cols: int
    description: str = ""
    slug: str = ""
    extra_panels: int = 10


class DisplayService:
    """Сервис создания и управления экранами."""

    def create_with_layout(
        self,
        spec: DisplayLayoutSpec,
        actor: "MsUser | None" = None,
    ) -> "Display":
        """
        Создать Display с ячейками и начальным набором панелей.

        Эквивалент legacy-поведения Display.save() для нового объекта.
        Используй вместо Display.objects.create() когда нужны cells+panels.

        Args:
            spec: параметры экрана
            actor: пользователь-создатель для ActivityLog

        Raises:
            ValueError: если rows или cols < 1
        """
        from apps.directory.displays.models import Cell, Display
        from apps.directory.panels.models import Panel
        from apps.core.references.models import Cities, Condition, Department

        if spec.rows < 1 or spec.cols < 1:
            raise ValueError(f"rows и cols должны быть >= 1, получено: {spec.rows}×{spec.cols}")

        with transaction.atomic():
            city = Cities.objects.get(name=spec.city_name)

            # 1. Создаём Display (чистый — без side effects)
            display = Display(
                name=spec.name,
                city=city,
                rows=spec.rows,
                cols=spec.cols,
                description=spec.description,
                slug=spec.slug or spec.name.lower(),
            )
            display.save()

            # 2. Ячейки
            cells = [
                Cell(display=display, row=row, col=col)
                for row in range(1, spec.rows + 1)
                for col in range(1, spec.cols + 1)
            ]
            Cell.objects.bulk_create(cells)

            # 3. Панели (cells + extra резервных)
            total_panels = len(cells) + spec.extra_panels
            monitor_dept = Department.objects.filter(name="monitor").first()
            work_condition = Condition.objects.filter(name="work").first()

            panels = [
                Panel(
                    name=f"{spec.name}-{i + 1}",
                    display=display,
                    comment="Создана автоматически с экраном",
                    condition=work_condition,
                    department=monitor_dept,
                )
                for i in range(total_panels)
            ]
            Panel.objects.bulk_create(panels)

            # 4. Назначаем панели ячейкам
            created_cells = list(Cell.objects.filter(display=display).order_by("id"))
            created_panels = list(Panel.objects.filter(display=display).order_by("id"))

            for cell, panel in zip(created_cells, created_panels, strict=False):
                cell.panel = panel
            Cell.objects.bulk_update(created_cells, ["panel"])

            # 5. ActivityLog (не старые HistoryReport)
            def _log_after_commit():
                activity_logger.log(
                    actor=actor,
                    target=display,
                    event_type="display_panel_replace",
                    description=f"Создан экран {display.name} ({spec.rows}×{spec.cols}), {len(cells)} ячеек",
                    payload={
                        "rows": spec.rows,
                        "cols": spec.cols,
                        "cells": len(cells),
                        "panels": len(panels),
                    },
                )

            transaction.on_commit(_log_after_commit)

            logger.info(
                "display_created_with_layout",
                display=display.name,
                rows=spec.rows,
                cols=spec.cols,
                cells=len(cells),
                panels=total_panels,
            )

        return display

    def replace_asset(self, display: "Display", asset_kind: str, uploaded_file) -> str:
        """Replace a display attachment and remove the previous physical file."""
        try:
            field_name = DISPLAY_ASSET_FIELDS[asset_kind]
        except KeyError as exc:
            raise ValueError(f"Неизвестный тип файла: {asset_kind}") from exc

        old_field = getattr(display, field_name)
        old_name = old_field.name if old_field else ""
        old_storage = old_field.storage if old_field else None

        setattr(display, field_name, uploaded_file)
        display.save(update_fields=[field_name])
        new_field = getattr(display, field_name)

        if old_name and old_storage and old_name != new_field.name and old_storage.exists(old_name):
            old_storage.delete(old_name)

        logger.info(
            "display_asset_replaced",
            display=display.name,
            asset_kind=asset_kind,
            file_name=new_field.name,
        )
        return new_field.url


# Глобальный синглтон
display_service = DisplayService()
