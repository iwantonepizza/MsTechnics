"""T-3-010: auth serializers."""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as _Base


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
        return token
