from rest_framework import serializers
from drf_spectacular.utils import OpenApiTypes, extend_schema_field

from apps.directory.panels.models import Panel
from apps.interface.api.v1.refs.serializers import ConditionSerializer


class PanelSerializer(serializers.ModelSerializer):
    condition = ConditionSerializer(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, allow_null=True)
    display_id = serializers.IntegerField(read_only=True)
    application_status_name = serializers.SerializerMethodField()
    cell_id = serializers.SerializerMethodField()

    class Meta:
        model = Panel
        fields = ["id", "name", "comment", "condition", "department_name",
                  "display_id", "cell_id", "application_status_name"]

    @extend_schema_field(OpenApiTypes.STR)
    def get_application_status_name(self, panel) -> str:
        return getattr(panel, "_active_application_status_name", None) or "default"

    @extend_schema_field(OpenApiTypes.INT)
    def get_cell_id(self, panel) -> int | None:
        try:
            return panel.cell.id
        except Exception:
            return None


class PanelPatchSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)
    condition_id = serializers.IntegerField(required=False)


class ChangeDepartmentSerializer(serializers.Serializer):
    department = serializers.CharField(required=True)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=500)


class MoveToCellSerializer(serializers.Serializer):
    cell_id = serializers.IntegerField(required=True)
    comment = serializers.CharField(required=False, allow_blank=True)
