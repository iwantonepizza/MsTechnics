"""
shared/exceptions.py — базовые доменные исключения.

Использование:
    from shared.exceptions import InvalidStateTransition, PanelHasActiveApplication
    raise InvalidStateTransition(f"Нельзя перейти из {current} в {target}")
"""


class DomainError(Exception):
    """Базовая ошибка доменной логики."""

    code: str = "domain_error"
    http_status: int = 400

    def __init__(self, message: str | None = None, **context):
        code = context.pop("code", None)
        http_status = context.pop("http_status", None)
        self.message = message or self.__class__.__doc__ or "Ошибка домена"
        self.context = context
        if code is not None:
            self.code = code
        if http_status is not None:
            self.http_status = http_status
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


class InvalidStateTransition(DomainError):
    """Запрошенный переход состояния недопустим."""

    code = "invalid_state_transition"


class PanelHasActiveApplication(DomainError):
    """Нельзя выполнить действие — у панели есть активная заявка."""

    code = "panel_has_active_application"


class PermissionDeniedForCity(DomainError):
    """Нет доступа к этому городу."""

    code = "forbidden_for_city"


class PermissionDeniedForDepartment(DomainError):
    """Нет доступа к этому отделу."""

    code = "forbidden_for_department"


class ObjectNotFound(DomainError):
    """Объект не найден."""

    code = "not_found"


# ---------------------------------------------------------------------------
# DRF Integration (T-3-004)
# ---------------------------------------------------------------------------
from rest_framework import status as _http_status


def _patch_domain_errors():
    """Добавляем http_status на существующие DomainError подклассы."""
    DomainError.http_status = _http_status.HTTP_400_BAD_REQUEST
    InvalidStateTransition.http_status = _http_status.HTTP_409_CONFLICT
    PanelHasActiveApplication.http_status = _http_status.HTTP_409_CONFLICT
    PermissionDeniedForCity.http_status = _http_status.HTTP_403_FORBIDDEN
    PermissionDeniedForDepartment.http_status = _http_status.HTTP_403_FORBIDDEN
    ObjectNotFound.http_status = _http_status.HTTP_404_NOT_FOUND


_patch_domain_errors()


class ConcurrentModification(DomainError):
    """Запись изменена параллельно."""
    code = "concurrent_modification"
    http_status = _http_status.HTTP_409_CONFLICT


def custom_exception_handler(exc, context):
    """
    Кастомный DRF exception handler.
    Формат: {"detail": "...", "code": "...", "errors": {...} | null}
    """
    from rest_framework.views import exception_handler as drf_handler
    from rest_framework.exceptions import ValidationError
    from rest_framework.response import Response

    if isinstance(exc, DomainError):
        return Response(
            {"detail": exc.message, "code": exc.code, "errors": None},
            status=getattr(exc, "http_status", 400),
        )

    response = drf_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, ValidationError):
        return Response(
            {"detail": "Ошибка валидации", "code": "validation_error",
             "errors": response.data if isinstance(response.data, dict) else None},
            status=_http_status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    data = response.data
    detail = data.get("detail") if isinstance(data, dict) else str(data)
    code = data.get("code") if isinstance(data, dict) else None
    response.data = {
        "detail": detail or "Ошибка",
        "code": code or _code_from_status(response.status_code),
        "errors": None,
    }
    return response


def _code_from_status(s: int) -> str:
    return {400: "bad_request", 401: "unauthorized", 403: "forbidden",
            404: "not_found", 405: "method_not_allowed", 409: "conflict",
            422: "validation_error", 429: "rate_limited"}.get(s, "error")
