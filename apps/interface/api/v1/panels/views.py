from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status as http_status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, mixins

from apps.directory.panels.models import Panel
from apps.directory.panels.services import panel_mover
from apps.activity.services import activity_logger
from shared.permissions import HasDepartmentAccess
from shared.throttling import TransitionRateThrottle
from .serializers import PanelSerializer, PanelPatchSerializer, ChangeDepartmentSerializer, MoveToCellSerializer


class PanelViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, GenericViewSet
):
    permission_classes = [IsAuthenticated]
    serializer_class = PanelSerializer
    http_method_names = ["get", "patch", "post", "head", "options"]

    def get_queryset(self):
        qs = (
            Panel.objects.with_application_status()
            .select_related("display", "department", "condition__color", "condition__icon")
        )
        params = self.request.query_params
        if d := params.get("display"):
            qs = qs.filter(display_id=d)
        if dept := params.get("department"):
            qs = qs.filter(department__name=dept)
        if cond := params.get("condition"):
            qs = qs.filter(condition__name=cond)
        user = self.request.user
        if user.permission not in ("admin", "all") and user.allowed_city.exists():
            qs = qs.filter(display__city__in=user.allowed_city.all())
        return qs.order_by("id")

    @extend_schema(tags=["panels"], summary="Список панелей",
                   parameters=[OpenApiParameter("display", int), OpenApiParameter("department", str)])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["panels"], summary="Детали панели")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=["panels"], summary="Обновить панель",
                   request=PanelPatchSerializer, responses=PanelSerializer)
    def partial_update(self, request, *args, **kwargs):
        panel = self.get_object()
        s = PanelPatchSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if "comment" in s.validated_data:
            panel.comment = s.validated_data["comment"]
            panel.save(update_fields=["comment"])
            activity_logger.log(event_type="panel.comment_added", target=panel, actor=request.user,
                                 description=f"Комментарий панели {panel.name} обновлён", comment=panel.comment)
        if "condition_id" in s.validated_data:
            from apps.core.references.models import Condition
            cond = Condition.objects.get(id=s.validated_data["condition_id"])
            panel_mover.change_condition(panel=panel, new_condition=cond, actor=request.user,
                                          comment=s.validated_data.get("comment", ""))
        panel.refresh_from_db()
        return Response(PanelSerializer(panel).data)

    @extend_schema(tags=["panels"], summary="Сменить отдел",
                   request=ChangeDepartmentSerializer, responses=PanelSerializer)
    @action(detail=True, methods=["post"], url_path="change-department",
            throttle_classes=[TransitionRateThrottle])
    def change_department(self, request, pk=None):
        panel = self.get_object()
        s = ChangeDepartmentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        panel_mover.move(panel=panel, to_department=s.validated_data["department"],
                          actor=request.user, comment=s.validated_data.get("comment", ""))
        panel.refresh_from_db()
        return Response(PanelSerializer(panel).data)

    @extend_schema(tags=["panels"], summary="Поставить панель в ячейку",
                   request=MoveToCellSerializer, responses=PanelSerializer)
    @action(detail=True, methods=["post"], url_path="move-to-cell",
            throttle_classes=[TransitionRateThrottle])
    def move_to_cell(self, request, pk=None):
        panel = self.get_object()
        s = MoveToCellSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        from apps.directory.displays.models import Cell
        cell = Cell.objects.get(id=s.validated_data["cell_id"])
        panel_mover.replace_in_cell(cell=cell, new_panel=panel, actor=request.user,
                                     comment=s.validated_data.get("comment", ""))
        panel.refresh_from_db()
        return Response(PanelSerializer(panel).data)

    @extend_schema(tags=["panels"], summary="История панели")
    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        panel = self.get_object()
        from apps.activity.models import ActivityLog
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(Panel)
        qs = ActivityLog.objects.filter(target_type=ct, target_id=panel.id).order_by("-occurred_at")
        if kind := request.query_params.get("kind"):
            qs = qs.filter(event_type__startswith=f"panel.{kind}")
        page = self.paginate_queryset(qs)
        from apps.interface.api.v1.activity.serializers import ActivityLogSerializer
        return self.get_paginated_response(ActivityLogSerializer(page, many=True).data)

    @extend_schema(tags=["panels"], summary="Заявки по панели")
    @action(detail=True, methods=["get"])
    def applications(self, request, pk=None):
        panel = self.get_object()
        from apps.workflow.applications.models import Application
        qs = Application.objects.filter(panel=panel).select_related("status", "display", "cell")
        if st := request.query_params.get("status"):
            qs = qs.filter(status__name=st)
        page = self.paginate_queryset(qs.order_by("-last_update_date_time"))
        from apps.interface.api.v1.applications.serializers import ApplicationListItemSerializer
        return self.get_paginated_response(ApplicationListItemSerializer(page, many=True).data)
