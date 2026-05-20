from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.core.users.permissions import get_role_names


class CityMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField(allow_null=True)


class MeSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    permission = serializers.CharField(read_only=True)
    roles = serializers.SerializerMethodField()
    extra_permissions = serializers.ListField(child=serializers.CharField(), read_only=True)
    allowed_cities = CityMiniSerializer(many=True, read_only=True, source="allowed_city")
    telegram_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    max_chat_id = serializers.CharField(required=False, allow_blank=True, allow_null=True, source="max_id")

    def get_roles(self, obj):
        return sorted(get_role_names(obj))


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value
