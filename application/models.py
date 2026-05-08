"""Compat shim for legacy `application` imports."""

from apps.workflow.applications.models import (
    Application,
    ApplicationEvent,
    ApplicationHistoryReport,
    ApplicationStatus,
)

__all__ = [
    "Application",
    "ApplicationEvent",
    "ApplicationHistoryReport",
    "ApplicationStatus",
]
