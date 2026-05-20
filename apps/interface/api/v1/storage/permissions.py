from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.core.users.permissions import has_perm


class CanManageStorageItems(BasePermission):
    """Allow storage writes for admin or users with can_edit_zip_counts."""

    def has_permission(self, request, _view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return has_perm(user, "can_edit_zip_counts")
