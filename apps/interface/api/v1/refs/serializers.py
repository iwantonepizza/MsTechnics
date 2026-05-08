"""T-3-011/012: справочники."""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.core.references.models import Color, Cities, Smile, Condition
from apps.core.references.models import Department
from apps.workflow.applications.models import ApplicationStatus
from apps.workflow.departures.models import DepartureStatus


class ColorSerializer(serializers.ModelSerializer):
    hex = serializers.CharField(source="hex_color")

    class Meta:
        model = Color
        fields = ["id", "name", "hex"]


class SmileSerializer(serializers.ModelSerializer):
    unicode_symbol = serializers.CharField(source="smile_icon")

    class Meta:
        model = Smile
        fields = ["id", "unicode_symbol"]


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Cities
        fields = ["id", "name", "description", "slug"]


class ConditionSerializer(serializers.ModelSerializer):
    color = ColorSerializer(read_only=True)
    icon = SmileSerializer(read_only=True)

    class Meta:
        model = Condition
        fields = ["id", "name", "description", "color", "icon"]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "description"]


class ApplicationStatusSerializer(serializers.ModelSerializer):
    color = ColorSerializer(read_only=True)
    color_text = ColorSerializer(read_only=True)
    icon = SmileSerializer(read_only=True)
    next_possible = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationStatus
        fields = ["id", "name", "description", "color", "color_text", "icon", "next_possible"]

    @extend_schema_field(
        {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "target_state": {"type": "string"},
                    "allowed_for": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["target_state", "allowed_for"],
            },
        }
    )
    def get_next_possible(self, obj) -> list[dict[str, object]]:
        try:
            from apps.workflow.applications.state_machine import application_fsm
            return [
                {"target_state": t.to_status, "allowed_for": list(t.allowed_roles)}
                for t in application_fsm.available_transitions_from(obj.name)
            ]
        except Exception:
            return []


class DepartureStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepartureStatus
        fields = ["id", "name", "description"]
