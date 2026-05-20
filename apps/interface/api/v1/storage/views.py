from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import ModelViewSet

from apps.directory.storage.models import Connectors, Hubs, Lamels, PowerBlocks, Wires

from .permissions import CanManageStorageItems
from .serializers import (
    ConnectorsSerializer,
    HubsSerializer,
    LamelsSerializer,
    PowerBlocksSerializer,
    WiresSerializer,
)


def _make_storage_viewset(model, serializer_cls, tag):
    class _VS(ModelViewSet):
        serializer_class = serializer_cls
        http_method_names = ["get", "post", "patch", "delete", "head", "options"]

        def get_queryset(self):
            return model.objects.order_by("id")

        @extend_schema(tags=[tag])
        def list(self, *args, **kwargs):
            return super().list(*args, **kwargs)

        def get_permissions(self):
            return [CanManageStorageItems()]

    _VS.__name__ = f"{model.__name__}ViewSet"
    return _VS


WiresViewSet = _make_storage_viewset(Wires, WiresSerializer, "storage")
HubsViewSet = _make_storage_viewset(Hubs, HubsSerializer, "storage")
LamelsViewSet = _make_storage_viewset(Lamels, LamelsSerializer, "storage")
PowerBlocksViewSet = _make_storage_viewset(PowerBlocks, PowerBlocksSerializer, "storage")
ConnectorsViewSet = _make_storage_viewset(Connectors, ConnectorsSerializer, "storage")
