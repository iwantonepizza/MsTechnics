from drf_spectacular.utils import OpenApiTypes, extend_schema_field
from rest_framework import serializers

from apps.directory.panels.models import Panel
from apps.interface.api.v1.refs.serializers import ConditionSerializer


class PanelSerializer(serializers.ModelSerializer):
    condition = ConditionSerializer(read_only=True)
    department_name = serializers.CharField(
        source="department.name", read_only=True, allow_null=True
    )
    display_id = serializers.IntegerField(read_only=True)
    application_status_name = serializers.SerializerMethodField()
    cell_id = serializers.SerializerMethodField()
    active_application_id = serializers.SerializerMethodField()

    class Meta:
        model = Panel
        fields = [
            "id",
            "name",
            "comment",
            "condition",
            "department_name",
            "display_id",
            "cell_id",
            "application_status_name",
            "active_application_id",
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_application_status_name(self, panel) -> str:
        return getattr(panel, "_active_application_status_name", None) or "default"

    @extend_schema_field(OpenApiTypes.INT)
    def get_cell_id(self, panel) -> int | None:
        try:
            return panel.cell.id
        except Exception:
            return None

    @extend_schema_field(OpenApiTypes.INT)
    def get_active_application_id(self, panel) -> int | None:
        active_application = panel.active_application
        return active_application.id if active_application else None


class PanelPatchSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)
    condition_id = serializers.IntegerField(required=False)


class ChangeDepartmentSerializer(serializers.Serializer):
    department = serializers.CharField(required=True)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)


class MoveToCellSerializer(serializers.Serializer):
    cell_id = serializers.IntegerField(required=True)
    comment = serializers.CharField(required=False, allow_blank=True)


class RemovePanelSerializer(serializers.Serializer):
    new_condition = serializers.CharField(required=False, allow_blank=False)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)
    application_id = serializers.IntegerField(required=False, allow_null=True)


class PanelCreateSerializer(serializers.Serializer):
    """T-7-035: создание панели через UI ZIP.

    Создаётся новая панель в указанном `display` со стартовым `condition` (по name).
    Поле `comment` опционально. Сразу попадает в department='zip' (склад).
    """

    name = serializers.CharField(required=True, max_length=15)
    display_id = serializers.IntegerField(required=True)
    condition_name = serializers.CharField(required=False, allow_blank=False, max_length=15)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)
