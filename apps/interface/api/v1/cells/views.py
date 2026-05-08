from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.directory.displays.models import Cell
from apps.directory.panels.services import panel_mover
from shared.throttling import TransitionRateThrottle
from .serializers import CellSerializer, AssignPanelSerializer


class CellViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CellSerializer

    def get_queryset(self):
        qs = Cell.objects.select_related(
            "display", "panel__condition__color", "panel__condition__icon", "panel__department"
        )
        if d := self.request.query_params.get("display"):
            qs = qs.filter(display_id=d)
        user = self.request.user
        if user.permission not in ("admin", "all"):
            qs = qs.filter(display__city__in=user.allowed_city.all())
        return qs.order_by("display", "row", "col")

    @extend_schema(tags=["cells"], summary="Список ячеек",
                   parameters=[OpenApiParameter("display", int)])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["cells"], summary="Ячейка")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=["cells"], summary="Назначить панель ячейке",
                   request=AssignPanelSerializer, responses=CellSerializer)
    @action(detail=True, methods=["post"], url_path="assign-panel",
            throttle_classes=[TransitionRateThrottle])
    def assign_panel(self, request, pk=None):
        cell = self.get_object()
        s = AssignPanelSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        from apps.directory.panels.models import Panel
        panel = Panel.objects.get(id=s.validated_data["panel_id"])
        panel_mover.replace_in_cell(cell=cell, new_panel=panel, actor=request.user,
                                     comment=s.validated_data.get("comment", ""))
        cell.refresh_from_db()
        return Response(CellSerializer(cell).data)
