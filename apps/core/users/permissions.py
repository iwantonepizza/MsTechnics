from __future__ import annotations

from django.db.models import Q

LEGACY_PERMISSION_TO_ROLES: dict[str, tuple[str, ...]] = {
    "monitoring": ("monitoring",),
    "control": ("control",),
    "service": ("service",),
    "all": ("monitoring", "control", "service"),
    "admin": ("admin",),
    "technical": ("technical",),
    "none_type": (),
}

EXTRA_PERMISSION_CHOICES: tuple[tuple[str, str], ...] = (
    ("can_edit_zip_counts", "Менять количество расходников ЗИП"),
    ("can_delete_panels", "Удалять панели"),
    ("can_send_password_reset", "Отправлять ссылки сброса пароля"),
)


def get_role_names(user) -> set[str]:
    if not user or not getattr(user, "is_authenticated", False):
        return set()

    role_names: set[str] = set()
    prefetched = getattr(user, "_prefetched_objects_cache", {}).get("roles")
    if prefetched is not None:
        role_names = {role.name for role in prefetched}
    elif getattr(user, "pk", None) and hasattr(user, "roles"):
        role_names = set(user.roles.values_list("name", flat=True))

    if role_names:
        return role_names

    permission = getattr(user, "permission", "none_type")
    return set(LEGACY_PERMISSION_TO_ROLES.get(permission, ()))


def has_role(user, *names: str) -> bool:
    return bool(get_role_names(user).intersection(names))


def is_admin(user) -> bool:
    return has_role(user, "admin")


def has_perm(user, perm: str) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if is_admin(user):
        return True
    extra_permissions = getattr(user, "extra_permissions", None) or []
    return perm in extra_permissions


def role_membership_q(*names: str) -> Q:
    requested_roles = {name for name in names if name}
    if not requested_roles:
        return Q(pk__in=[])

    legacy_permissions = {
        permission
        for permission, roles in LEGACY_PERMISSION_TO_ROLES.items()
        if requested_roles.intersection(roles)
    }
    query = Q(roles__name__in=requested_roles)
    if legacy_permissions:
        query |= Q(roles__isnull=True, permission__in=legacy_permissions)
    return query
