"""Compat shim for legacy `departure` imports."""

from apps.workflow.departures.models import (
    Contact,
    Departure,
    DepartureHistoryReport,
    DepartureStatus,
    DepartureStatusName,
    Executor,
)

__all__ = [
    "Contact",
    "Departure",
    "DepartureHistoryReport",
    "DepartureStatus",
    "DepartureStatusName",
    "Executor",
]
