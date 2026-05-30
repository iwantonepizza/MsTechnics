from rest_framework import serializers

from apps.workflow.daily_tasks.models import DailyTask


class DailyTaskSerializer(serializers.ModelSerializer):
    city_id = serializers.IntegerField(read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    available = serializers.SerializerMethodField()

    class Meta:
        model = DailyTask
        fields = [
            "id",
            "name",
            "description",
            "status",
            "start_time",
            "end_time",
            "link",
            "city_id",
            "city_name",
            "available",
        ]

    def get_available(self, task) -> bool:
        return task.check_available_status()
