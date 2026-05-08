"""Compat shim for legacy `user` imports."""

from apps.core.users.models import MsUser

ConcreteMsUser = MsUser

__all__ = ["ConcreteMsUser", "MsUser"]
