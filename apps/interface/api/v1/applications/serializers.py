from rest_framework import serializers
from drf_spectacular.utils import OpenApiTypes, extend_schema_field

from apps.workflow.applications.models import Application, ApplicationEvent
from apps.interface.api.v1.refs.serializers import ApplicationStatusSerializer, CitySerializer


class DisplayMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    slug = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_null=True)


class PanelMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class CellMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    position = serializers.CharField(allow_null=True)


class ExecutorMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


class ApplicationListItemSerializer(serializers.ModelSerializer):
    status = ApplicationStatusSerializer(read_only=True)
    display = DisplayMiniSerializer(read_only=True)
    panel = PanelMiniSerializer(read_only=True)
    cell = CellMiniSerializer(read_only=True)

    class Meta:
        model = Application
        fields = ["id", "status", "display", "panel", "cell", "last_update_date_time"]


class ApplicationDetailSerializer(serializers.ModelSerializer):
    status = ApplicationStatusSerializer(read_only=True)
    display = DisplayMiniSerializer(read_only=True)
    panel = PanelMiniSerializer(read_only=True)
    cell = CellMiniSerializer(read_only=True)
    executor = ExecutorMiniSerializer(read_only=True, allow_null=True)
    initial_comment = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = ["id", "status", "display", "panel", "cell", "executor",
                  "initial_comment", "last_update_date_time"]

    @extend_schema_field(OpenApiTypes.STR)
    def get_initial_comment(self, obj) -> str:
        ev = obj.events.order_by("occurred_at").first()
        if ev:
            return ev.comment
        return getattr(obj, "comment_monitoring", "") or ""


class ApplicationCreateSerializer(serializers.Serializer):
    display_id = serializers.IntegerField(required=True)
    panel_id   = serializers.IntegerField(required=True)
    cell_id    = serializers.IntegerField(required=True)
    comment    = serializers.CharField(required=True, max_length=2000)
    file       = serializers.FileField(required=False, allow_null=True)


class TransitionSerializer(serializers.Serializer):
    target_state = serializers.CharField(required=True)
    comment      = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    executor_id  = serializers.IntegerField(required=False, allow_null=True)
    file         = serializers.FileField(required=False, allow_null=True)

    def validate_target_state(self, value):
        from apps.workflow.applications.state_machine import application_fsm
        all_targets = {t.to_status for t in application_fsm.all_transitions()}
        if value not in all_targets:
            raise serializers.ValidationError(f"Неизвестный target_state: {value}")
        return value


class ApplicationEventSerializer(serializers.ModelSerializer):
    user      = serializers.SerializerMethodField()
    timestamp = serializers.DateTimeField(source="occurred_at")
    file_url  = serializers.SerializerMethodField()
    state_from = serializers.SerializerMethodField()
    state_to   = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationEvent
        fields = ["id", "stage", "user", "timestamp", "comment",
                  "file_url", "state_from", "state_to"]

    @extend_schema_field(OpenApiTypes.STR)
    def get_user(self, obj) -> str:
        return obj.actor_name or ""

    @extend_schema_field(OpenApiTypes.URI)
    def get_file_url(self, obj) -> str | None:
        return obj.file.url if obj.file else None

    @extend_schema_field(OpenApiTypes.STR)
    def get_state_from(self, obj) -> str:
        payload = getattr(obj, "_state_from", None) or ""
        return payload

    @extend_schema_field(OpenApiTypes.STR)
    def get_state_to(self, obj) -> str:
        return obj.stage
