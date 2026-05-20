from drf_spectacular.utils import OpenApiTypes, extend_schema_field
from rest_framework import serializers

from apps.directory.displays.models import Cell, Display
from apps.directory.panels.models import Panel
from apps.interface.api.v1.refs.serializers import CitySerializer, ConditionSerializer


class PanelOnCellSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    condition = ConditionSerializer(read_only=True)
    application_status_name = serializers.SerializerMethodField()
    comment = serializers.CharField(allow_null=True)

    @extend_schema_field(OpenApiTypes.STR)
    def get_application_status_name(self, panel) -> str:
        val = getattr(panel, "_active_application_status_name", None)
        return val or "default"


class CellSerializer(serializers.ModelSerializer):
    panel = PanelOnCellSerializer(read_only=True)
    position = serializers.CharField()

    class Meta:
        model = Cell
        fields = ["id", "position", "row", "col", "panel"]


class DisplayListSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    aggregated_condition = serializers.SerializerMethodField()

    class Meta:
        model = Display
        fields = [
            "id",
            "name",
            "description",
            "slug",
            "city",
            "rows",
            "cols",
            "aggregated_condition",
        ]

    @extend_schema_field(ConditionSerializer(allow_null=True))
    def get_aggregated_condition(self, display):
        prefetched_cells = getattr(display, "_prefetched_objects_cache", {}).get("cell_set")
        if prefetched_cells is not None:
            worst_condition = None
            worst_condition_id = -1
            for cell in prefetched_cells:
                panel = getattr(cell, "panel", None)
                condition = getattr(panel, "condition", None)
                if condition is None:
                    continue
                if condition.id > worst_condition_id:
                    worst_condition = condition
                    worst_condition_id = condition.id
            if worst_condition is None:
                return None
            return ConditionSerializer(worst_condition).data

        condition = display.current_condition
        if condition is None:
            return None
        return ConditionSerializer(condition).data


class DisplayDetailSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    cells = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    project_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Display
        fields = [
            "id",
            "name",
            "description",
            "slug",
            "city",
            "rows",
            "cols",
            "file_url",
            "project_photo_url",
            "cells",
        ]

    @extend_schema_field(CellSerializer(many=True))
    def get_cells(self, display):
        cells = list(
            Cell.objects.filter(display=display)
            .select_related("panel__condition__color", "panel__condition__icon")
            .order_by("row", "col")
        )
        # annotate panels
        panel_ids = [c.panel_id for c in cells if c.panel_id]
        try:
            annotated = {
                p.id: p for p in Panel.objects.filter(id__in=panel_ids).with_application_status()
            }
            for c in cells:
                if c.panel_id and c.panel_id in annotated:
                    c.panel = annotated[c.panel_id]
        except Exception:
            pass
        return CellSerializer(cells, many=True).data

    @extend_schema_field(OpenApiTypes.URI)
    def get_file_url(self, d) -> str | None:
        return d.file.url if d.file else None

    @extend_schema_field(OpenApiTypes.URI)
    def get_project_photo_url(self, d) -> str | None:
        return d.project_photo.url if d.project_photo else None


class PhotoUploadSerializer(serializers.Serializer):
    file = serializers.ImageField(required=True)
    description = serializers.CharField(max_length=200, required=False, allow_blank=True)


class AlarmEventSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    type = serializers.CharField()
    receiving_card_no = serializers.IntegerField()
    raw_position = serializers.CharField()
    raw_email_subject = serializers.CharField()
    occurred_at = serializers.DateTimeField()
    resolved_at = serializers.DateTimeField(allow_null=True)
    cell_id = serializers.IntegerField(allow_null=True)
    cell_position = serializers.SerializerMethodField()
    panel_id = serializers.IntegerField(allow_null=True)
    panel_name = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_cell_position(self, alarm) -> str | None:
        return alarm.cell.position if alarm.cell else None

    @extend_schema_field(OpenApiTypes.STR)
    def get_panel_name(self, alarm) -> str | None:
        return alarm.panel.name if alarm.panel else None
