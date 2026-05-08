from rest_framework import serializers
from apps.directory.displays.models import Cell
from apps.interface.api.v1.panels.serializers import PanelSerializer


class CellSerializer(serializers.ModelSerializer):
    panel = PanelSerializer(read_only=True)
    position = serializers.CharField(read_only=True)

    class Meta:
        model = Cell
        fields = ["id", "position", "row", "col", "panel", "display_id"]


class AssignPanelSerializer(serializers.Serializer):
    panel_id = serializers.IntegerField(required=True)
    comment = serializers.CharField(required=False, allow_blank=True)
