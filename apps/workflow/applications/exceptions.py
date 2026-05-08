"""apps/workflow/applications/exceptions.py"""
from shared.exceptions import DomainError


class InvalidTransition(DomainError):
    """Переход между статусами заявки недопустим."""
    code = "invalid_state_transition"
    http_status = 409


class TransitionPermissionDenied(DomainError):
    """У пользователя нет прав выполнить этот переход."""
    code = "transition_permission_denied"
    http_status = 403


class ApplicationNotFound(DomainError):
    """Заявка не найдена."""
    code = "application_not_found"
    http_status = 404
