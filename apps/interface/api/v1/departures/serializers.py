from rest_framework import serializers
from apps.workflow.departures.models import Departure, Contact, Executor
from apps.interface.api.v1.refs.serializers import DepartureStatusSerializer


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["id", "first_name", "last_name", "description", "phone_number", "telegram_id"]


class ExecutorMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


class ExecutorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Executor
        fields = ["id", "first_name", "last_name", "executor_role", "phone_number", "telegram_id"]


class DepartureListSerializer(serializers.ModelSerializer):
    status = DepartureStatusSerializer(read_only=True, allow_null=True)
    executor = ExecutorMiniSerializer(read_only=True, allow_null=True)

    class Meta:
        model = Departure
        fields = ["id", "description", "status", "executor",
                  "time_start", "time_end", "time_updated"]


class DepartureCreateSerializer(serializers.Serializer):
    description = serializers.CharField(required=True, max_length=1000)
    executor_id = serializers.IntegerField(required=False, allow_null=True)
    time_start = serializers.DateTimeField(required=False, allow_null=True)


class DeparturePatchSerializer(serializers.Serializer):
    description = serializers.CharField(required=False, max_length=1000)
    executor_id = serializers.IntegerField(required=False, allow_null=True)
    time_start = serializers.DateTimeField(required=False, allow_null=True)


class DepartureCompleteSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True)
    time_end = serializers.DateTimeField(required=False)
