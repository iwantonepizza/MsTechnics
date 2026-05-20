from rest_framework import serializers


class DisplaySearchItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    slug = serializers.CharField(allow_null=True)
    city_name = serializers.CharField()
    city_slug = serializers.CharField(allow_null=True)
    score = serializers.FloatField()


class PanelSearchItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    display_name = serializers.CharField(allow_null=True)
    display_slug = serializers.CharField(allow_null=True)
    city_slug = serializers.CharField(allow_null=True)
    condition_name = serializers.CharField(allow_null=True)
    department_name = serializers.CharField(allow_null=True)
    active_application_id = serializers.IntegerField(allow_null=True)
    score = serializers.FloatField()


class ApplicationSearchItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    display_name = serializers.CharField(allow_null=True)
    display_slug = serializers.CharField(allow_null=True)
    city_slug = serializers.CharField(allow_null=True)
    panel_name = serializers.CharField(allow_null=True)
    cell_position = serializers.CharField(allow_null=True)
    status_name = serializers.CharField(allow_null=True)
    initial_comment = serializers.CharField(allow_null=True)
    score = serializers.FloatField()


class DepartureSearchItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    description = serializers.CharField(allow_null=True)
    executor_name = serializers.CharField(allow_null=True)
    status_name = serializers.CharField(allow_null=True)
    score = serializers.FloatField()


class UserSearchItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.CharField()
    permission = serializers.CharField()
    score = serializers.FloatField()


class StorageSearchItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    kind = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    count = serializers.IntegerField()
    score = serializers.FloatField()


class GlobalSearchResponseSerializer(serializers.Serializer):
    displays = DisplaySearchItemSerializer(many=True)
    panels = PanelSearchItemSerializer(many=True)
    applications = ApplicationSearchItemSerializer(many=True)
    departures = DepartureSearchItemSerializer(many=True)
    users = UserSearchItemSerializer(many=True)
    storage = StorageSearchItemSerializer(many=True)
