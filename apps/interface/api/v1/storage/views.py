from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from apps.directory.storage.models import Wires, Hubs, Lamels
from shared.permissions import HasDepartmentAccess
from .serializers import WiresSerializer, HubsSerializer, LamelsSerializer


def _make_storage_viewset(model, serializer_cls, tag):
    class _VS(ModelViewSet):
        serializer_class = serializer_cls
        http_method_names = ["get", "patch", "delete", "head", "options"]

        def get_queryset(self):
            qs = model.objects.all()
            if slug := self.request.query_params.get("display"):
                qs = qs.filter(display__slug=slug)
            return qs.order_by("id")

        def get_permissions(self):
            if self.action in ("partial_update", "destroy"):
                return [HasDepartmentAccess.for_("control", "admin", "all")()]
            return [IsAuthenticated()]

        @extend_schema(tags=[tag], parameters=[OpenApiParameter("display", str)])
        def list(self, *args, **kwargs):
            return super().list(*args, **kwargs)

    _VS.__name__ = f"{model.__name__}ViewSet"
    return _VS


WiresViewSet  = _make_storage_viewset(Wires,  WiresSerializer,  "storage")
HubsViewSet   = _make_storage_viewset(Hubs,   HubsSerializer,   "storage")
LamelsViewSet = _make_storage_viewset(Lamels, LamelsSerializer, "storage")
