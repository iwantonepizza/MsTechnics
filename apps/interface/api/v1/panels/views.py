# ruff: noqa: RUF001
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.activity.services import activity_logger
from apps.core.users.permissions import is_admin
from apps.directory.panels.models import Panel
from apps.directory.panels.services import delete_panel, panel_mover
from shared.exceptions import DomainError
from shared.permissions import HasDepartmentAccess
from shared.throttling import TransitionRateThrottle

from .serializers import (
    ChangeDepartmentSerializer,
    MoveToCellSerializer,
    PanelCreateSerializer,
    PanelPatchSerializer,
    PanelSerializer,
    RemovePanelSerializer,
)


class PanelViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = PanelSerializer
    http_method_names = ["get", "patch", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = Panel.objects.with_application_status().select_related(
            "display", "department", "condition__color", "condition__icon"
        )
        params = self.request.query_params
        if d := params.get("display"):
            qs = qs.filter(display_id=d)
        if dept := params.get("department"):
            qs = qs.filter(department__name=dept)
        if cond := params.get("condition"):
            qs = qs.filter(condition__name=cond)
        user = self.request.user
        if not is_admin(user) and user.allowed_city.exists():
            qs = qs.filter(display__city__in=user.allowed_city.all())
        return qs.order_by("id")

    def get_permissions(self):
        if self.action == "remove":
            return [HasDepartmentAccess.for_("service", "admin")()]
        if self.action == "create":
            # T-7-035: создать панель может admin или сервис (Z7).
            return [HasDepartmentAccess.for_("service", "admin")()]
        if self.action == "destroy":
            # T-7-036: удалить — только админ (Z8).
            return [HasDepartmentAccess.for_("admin")()]
        return [permission() for permission in self.permission_classes]

    @extend_schema(
        tags=["panels"],
        summary="Список панелей",
        parameters=[OpenApiParameter("display", int), OpenApiParameter("department", str)],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["panels"], summary="Детали панели")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=["panels"],
        summary="Создать новую панель (T-7-035, Z7)",
        request=PanelCreateSerializer,
        responses=PanelSerializer,
    )
    def create(self, request, *_args, **_kwargs):
        from apps.core.references.models import Condition, Department
        from apps.directory.displays.models import Display

        s = PanelCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        display = Display.objects.filter(id=s.validated_data["display_id"]).first()
        if display is None:
            raise DomainError(
                f"Экран #{s.validated_data['display_id']} не найден.",
                code="invalid_display",
            )

        condition = None
        if cn := s.validated_data.get("condition_name"):
            condition = Condition.objects.filter(name=cn).first()
            if condition is None:
                raise DomainError(f"Состояние '{cn}' не найдено.", code="invalid_condition")

        zip_dept = Department.objects.filter(name="zip").first()

        if Panel.objects.filter(name=s.validated_data["name"]).exists():
            raise DomainError(
                f"Панель '{s.validated_data['name']}' уже существует.",
                code="duplicate_panel_name",
            )

        panel = Panel.objects.create(
            name=s.validated_data["name"],
            display=display,
            condition=condition,
            department=zip_dept,
            comment=s.validated_data.get("comment", ""),
        )
        activity_logger.log(
            event_type="panel.created",
            target=panel,
            actor=request.user,
            description=f"Создана панель {panel.name} (экран {display.name})",
        )
        return Response(PanelSerializer(panel).data, status=201)

    @extend_schema(tags=["panels"], summary="Удалить панель (T-7-036, admin-only, Z8)")
    def destroy(self, request, *_args, **_kwargs):
        panel = self.get_object()
        delete_panel(panel=panel, actor=request.user)
        return Response(status=204)

    @extend_schema(
        tags=["panels"],
        summary="Обновить панель",
        request=PanelPatchSerializer,
        responses=PanelSerializer,
    )
    def partial_update(self, request, *_args, **_kwargs):
        panel = self.get_object()
        s = PanelPatchSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if "comment" in s.validated_data:
            panel.comment = s.validated_data["comment"]
            panel.save(update_fields=["comment"])
            activity_logger.log(
                event_type="panel.comment_added",
                target=panel,
                actor=request.user,
                description=f"Комментарий панели {panel.name} обновлён",
                comment=panel.comment,
            )
        if "condition_id" in s.validated_data:
            from apps.core.references.models import Condition

            cond = Condition.objects.get(id=s.validated_data["condition_id"])
            panel_mover.change_condition(
                panel=panel,
                new_condition=cond,
                actor=request.user,
                comment=s.validated_data.get("comment", ""),
            )
        panel.refresh_from_db()
        return Response(PanelSerializer(panel).data)

    @extend_schema(
        tags=["panels"],
        summary="Сменить отдел",
        request=ChangeDepartmentSerializer,
        responses=PanelSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="change-department",
        throttle_classes=[TransitionRateThrottle],
    )
    def change_department(self, request, *_args, **_kwargs):
        panel = self.get_object()
        s = ChangeDepartmentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        panel_mover.move(
            panel=panel,
            to_department=s.validated_data["department"],
            actor=request.user,
            comment=s.validated_data.get("comment", ""),
        )
        panel.refresh_from_db()
        return Response(PanelSerializer(panel).data)

    @extend_schema(
        tags=["panels"],
        summary="Поставить панель в ячейку",
        request=MoveToCellSerializer,
        responses=PanelSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="move-to-cell",
        throttle_classes=[TransitionRateThrottle],
    )
    def move_to_cell(self, request, *_args, **_kwargs):
        panel = self.get_object()
        s = MoveToCellSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        from apps.directory.displays.models import Cell

        cell = Cell.objects.get(id=s.validated_data["cell_id"])
        panel_mover.replace_in_cell(
            cell=cell,
            new_panel=panel,
            actor=request.user,
            comment=s.validated_data.get("comment", ""),
        )
        panel.refresh_from_db()
        return Response(PanelSerializer(panel).data)

    @extend_schema(
        tags=["panels"],
        summary="Снять панель с ячейки",
        request=RemovePanelSerializer,
        responses=PanelSerializer,
    )
    @action(
        detail=True, methods=["post"], url_path="remove", throttle_classes=[TransitionRateThrottle]
    )
    def remove(self, request, *_args, **_kwargs):
        panel = self.get_object()
        s = RemovePanelSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        new_condition = None
        if condition_name := s.validated_data.get("new_condition"):
            from apps.core.references.models import Condition

            new_condition = Condition.objects.filter(name=condition_name).first()
            if new_condition is None:
                raise DomainError(
                    f"Состояние '{condition_name}' не найдено.",
                    code="invalid_condition",
                )

        application = None
        if application_id := s.validated_data.get("application_id"):
            from apps.workflow.applications.models import Application

            application = Application.objects.filter(id=application_id, panel=panel).first()
            if application is None:
                raise DomainError(
                    f"Заявка #{application_id} не связана с панелью {panel.name}.",
                    code="invalid_application_context",
                )

        panel_mover.remove_from_cell(
            panel=panel,
            actor=request.user,
            new_condition=new_condition,
            comment=s.validated_data.get("comment", ""),
            application=application,
        )
        panel.refresh_from_db()
        return Response(PanelSerializer(panel).data)

    @extend_schema(tags=["panels"], summary="История панели")
    @action(detail=True, methods=["get"])
    def history(self, request, *_args, **_kwargs):
        panel = self.get_object()
        from django.contrib.contenttypes.models import ContentType

        from apps.activity.models import ActivityLog

        ct = ContentType.objects.get_for_model(Panel)
        qs = ActivityLog.objects.filter(target_type=ct, target_id=panel.id).order_by("-occurred_at")
        if kind := request.query_params.get("kind"):
            qs = qs.filter(event_type__startswith=f"panel.{kind}")
        page = self.paginate_queryset(qs)
        from apps.interface.api.v1.activity.serializers import ActivityLogSerializer

        return self.get_paginated_response(ActivityLogSerializer(page, many=True).data)

    @extend_schema(tags=["panels"], summary="Заявки по панели")
    @action(detail=True, methods=["get"])
    def applications(self, request, *_args, **_kwargs):
        panel = self.get_object()
        from apps.workflow.applications.models import Application

        qs = Application.objects.filter(panel=panel).select_related(
            "status",
            "status__color",
            "status__color_text",
            "status__icon",
            "display",
            "display__city",
            "cell",
        )
        if st := request.query_params.get("status"):
            qs = qs.filter(status__name=st)
        page = self.paginate_queryset(qs.order_by("-last_update_date_time"))
        from apps.interface.api.v1.applications.serializers import ApplicationListItemSerializer

        return self.get_paginated_response(ApplicationListItemSerializer(page, many=True).data)
