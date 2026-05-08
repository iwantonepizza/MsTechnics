from rest_framework import serializers
from apps.directory.storage.models import Wires, Hubs, Lamels


class StorageItemBaseSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ["id", "name", "count", "description"]


class WiresSerializer(StorageItemBaseSerializer):
    class Meta(StorageItemBaseSerializer.Meta):
        model = Wires


class HubsSerializer(StorageItemBaseSerializer):
    class Meta(StorageItemBaseSerializer.Meta):
        model = Hubs


class LamelsSerializer(StorageItemBaseSerializer):
    class Meta(StorageItemBaseSerializer.Meta):
        model = Lamels


class StoragePatchSerializer(serializers.Serializer):
    count = serializers.IntegerField(required=False, min_value=0)
    description = serializers.CharField(required=False, allow_blank=True)
