"""
shared/permissions.py — T-3-003: единые DRF permissions.

Использование:
    permission_classes = [IsAuthenticated, HasDepartmentAccess.for_("control")]
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.core.users.permissions import has_role, is_admin

DEPARTMENT_ALL   = "all"
DEPARTMENT_ADMIN = "admin"
DEPARTMENT_MON   = "monitoring"
DEPARTMENT_CTRL  = "control"
DEPARTMENT_SVC   = "service"
DEPARTMENT_TECH  = "technical"
DEPARTMENT_NONE  = "none_type"


class HasDepartmentAccess(BasePermission):
    """
    Параметризованный permission по роли.
    Использование: HasDepartmentAccess.for_("control", "admin")
    """
    required_departments: tuple = ()

    @classmethod
    def for_(cls, *departments: str):
        return type(
            f"{cls.__name__}_{'_'.join(departments)}",
            (cls,),
            {"required_departments": tuple(departments)},
        )

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        return has_role(request.user, *self.required_departments)


class HasCityAccess(BasePermission):
    """Object-level: проверяет allowed_city юзера."""

    def has_permission(self, request, view) -> bool:
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        if is_admin(user):
            return True
        city_id = self._city_id(obj)
        if city_id is None:
            return True
        return user.allowed_city.filter(id=city_id).exists()

    @staticmethod
    def _city_id(obj):
        if hasattr(obj, "city_id"):
            return obj.city_id
        if hasattr(obj, "display") and obj.display:
            return getattr(obj.display, "city_id", None)
        if hasattr(obj, "panel") and obj.panel and obj.panel.display:
            return getattr(obj.panel.display, "city_id", None)
        if hasattr(obj, "cell") and obj.cell and obj.cell.display:
            return getattr(obj.cell.display, "city_id", None)
        return None


class IsAdmin(BasePermission):
    """Только admin."""
    def has_permission(self, request, view) -> bool:
        return request.user.is_authenticated and is_admin(request.user)


class CanCreateApplication(BasePermission):
    """Only monitoring/admin/all can create applications."""
    ALLOWED = (DEPARTMENT_MON, DEPARTMENT_ADMIN, DEPARTMENT_ALL)

    def has_permission(self, request, view) -> bool:
        return request.user.is_authenticated and has_role(request.user, *self.ALLOWED)


class CanTransitionApplication(BasePermission):
    """Object-level: проверяет через FSM что роль может сделать запрошенный transition."""

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        if is_admin(user):
            return True
        target = request.data.get("target_state", "")
        if not target:
            return False
        try:
            from apps.workflow.applications.state_machine import application_fsm
            transition = application_fsm.get_transition(obj.status.name, target)
            return has_role(user, *transition.allowed_roles)
        except Exception:
            return False
