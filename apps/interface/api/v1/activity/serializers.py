from rest_framework import serializers
from apps.activity.models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    target_kind = serializers.SerializerMethodField()
    target_summary = serializers.SerializerMethodField()
    actor_name = serializers.CharField()

    class Meta:
        model = ActivityLog
        fields = ["id", "event_type", "target_kind", "target_id", "target_summary",
                  "actor_name", "occurred_at", "description", "comment", "payload"]

    def get_target_kind(self, obj):
        return obj.target_type.model if obj.target_type else None

    def get_target_summary(self, obj):
        if not obj.target_type:
            return None
        return {"kind": obj.target_type.model, "id": obj.target_id}
