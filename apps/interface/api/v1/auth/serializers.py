"""T-3-010: auth serializers."""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as _Base

from apps.core.users.permissions import get_role_names


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, max_length=150)
    password = serializers.CharField(required=True, max_length=128, write_only=True)


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()


class TokenObtainPairSerializer(_Base):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["permission"] = user.permission
        token["roles"] = sorted(get_role_names(user))
        token["extra_permissions"] = list(user.extra_permissions or [])
        return token
