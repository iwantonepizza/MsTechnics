from rest_framework import serializers

from apps.directory.storage.models import Connectors, Hubs, Lamels, PowerBlocks, Wires


class StorageItemBaseSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        fields = [
            "id",
            "name",
            "count",
            "description",
            "low_stock_threshold",
            "is_low_stock",
            "photo",
        ]
        read_only_fields = ["is_low_stock"]


class WiresSerializer(StorageItemBaseSerializer):
    class Meta(StorageItemBaseSerializer.Meta):
        model = Wires


class HubsSerializer(StorageItemBaseSerializer):
    class Meta(StorageItemBaseSerializer.Meta):
        model = Hubs


class LamelsSerializer(StorageItemBaseSerializer):
    class Meta(StorageItemBaseSerializer.Meta):
        model = Lamels


class PowerBlocksSerializer(StorageItemBaseSerializer):
    class Meta(StorageItemBaseSerializer.Meta):
        model = PowerBlocks


class ConnectorsSerializer(StorageItemBaseSerializer):
    class Meta(StorageItemBaseSerializer.Meta):
        model = Connectors
