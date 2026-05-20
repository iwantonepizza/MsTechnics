from datetime import timedelta
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework import status as http_status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, mixins

from apps.core.users.permissions import is_admin
from apps.workflow.applications.models import Application
from apps.workflow.applications.services import application_service
from shared.exceptions import DomainError
from shared.permissions import CanCreateApplication, CanTransitionApplication
from shared.throttling import TransitionRateThrottle
from .filters import apply_box_filter
from .serializers import (
    ApplicationListItemSerializer, ApplicationDetailSerializer,
    ApplicationCreateSerializer, TransitionSerializer, ApplicationEventSerializer,
)


class ApplicationViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin,
    mixins.CreateModelMixin, mixins.DestroyModelMixin,
    GenericViewSet
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Application.objects.select_related(
            "status", "status__color", "status__color_text", "status__icon",
            "display", "display__city", "panel", "cell", "executor",
        )
        params = self.request.query_params
        if slug := params.get("display"):
            qs = qs.filter(display__slug=slug)
        if cell := params.get("cell"):
            qs = qs.filter(cell__id=cell)
        if panel_id := params.get("panel"):
            qs = qs.filter(panel_id=panel_id)
        if self.action == "list":
            box = params.get("box", "received")
            qs = apply_box_filter(qs, box)
        user = self.request.user
        if not is_admin(user) and user.allowed_city.exists():
            qs = qs.filter(display__city__in=user.allowed_city.all())
        ordering = params.get("ordering", "-last_update_date_time,-id")
        return qs.order_by(*ordering.split(","))

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ApplicationDetailSerializer
        if self.action == "create":
            return ApplicationCreateSerializer
        return ApplicationListItemSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), CanCreateApplication()]
        return [IsAuthenticated()]

    @extend_schema(tags=["applications"], summary="Список заявок",
                   parameters=[OpenApiParameter("display", str), OpenApiParameter("box", str),
                                OpenApiParameter("panel", int), OpenApiParameter("cell", int)])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["applications"], summary="Детали заявки")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=["applications"], summary="Создать заявку",
                   request=ApplicationCreateSerializer)
    def create(self, request, *args, **kwargs):
        s = ApplicationCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        from apps.directory.panels.models import Panel
        from apps.directory.displays.models import Cell
        from django.utils import timezone
        panel = Panel.objects.get(id=s.validated_data["panel_id"])
        cell = Cell.objects.get(id=s.validated_data["cell_id"])
        app = application_service.create(
            panel=panel,
            comment=s.validated_data["comment"],
            time_event=timezone.now(),
            user=request.user,
            file=s.validated_data.get("file"),
        )
        return Response(ApplicationDetailSerializer(app).data, status=http_status.HTTP_201_CREATED)

    @extend_schema(tags=["applications"], summary="Удалить заявку")
    def destroy(self, request, *args, **kwargs):
        """
        T-3-fix-002 / B3: Whitelist-подход — разрешено только is_creator OR is_admin.
        Если creator is None (старая заявка) — не-admin НЕ проходит.
        """
        app = self.get_object()

        # 1. Только статус sent_to_control
        if app.status.name != "sent_to_control":
            raise DomainError(
                "Удалять можно только заявки в статусе sent_to_control",
                code="delete_status_invalid",
            )

        # 2. Окно 5 минут с момента создания
        created = getattr(app, "time_monitoring", None) or app.last_update_date_time
        if created and timezone.now() - created > timedelta(minutes=5):
            raise DomainError(
                "Окно для удаления истекло (5 минут)",
                code="delete_window_expired",
            )

        # 3. Whitelist: только создатель ИЛИ admin/all
        creator = getattr(app, "user_monitoring", None)
        admin_access = is_admin(request.user)
        is_creator = bool(creator and creator == request.user.username)

        if not (is_creator or admin_access):
            raise DomainError(
                "Удалить может только создатель заявки",
                code="forbidden",
                http_status=http_status.HTTP_403_FORBIDDEN,
            )

        # 4. Audit log перед удалением — запись останется даже после delete()
        from apps.activity.services import activity_logger
        activity_logger.log(
            actor=request.user,
            target=app,
            event_type="application.deleted",
            description=f"Удалена заявка #{app.id}",
            comment="Удаление в окно 5 минут",
        )

        app.delete()
        return Response(status=http_status.HTTP_204_NO_CONTENT)

    # ── T-3-031: transition ──────────────────────────────────────────────
    @extend_schema(tags=["applications"], summary="Перевести заявку (FSM)",
                   request=TransitionSerializer,
                   responses={200: ApplicationDetailSerializer, 409: None, 403: None})
    @action(detail=True, methods=["post"], url_path="transition",
            parser_classes=[MultiPartParser, FormParser, JSONParser],
            permission_classes=[IsAuthenticated, CanTransitionApplication],
            throttle_classes=[TransitionRateThrottle])
    def transition(self, request, pk=None):
        app = self.get_object()
        self.check_object_permissions(request, app)
        s = TransitionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        executor = None
        if eid := s.validated_data.get("executor_id"):
            from apps.workflow.departures.models import Executor
            try:
                executor = Executor.objects.get(id=eid)
            except Executor.DoesNotExist:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"executor_id": ["Исполнитель не найден"]})
        app = application_service.transition(
            application=app, target_status=s.validated_data["target_state"],
            actor=request.user, comment=s.validated_data.get("comment", ""),
            file=s.validated_data.get("file"),
        )
        if executor:
            app = application_service.set_executor(
                application=app,
                executor=executor,
                actor=request.user,
                comment=s.validated_data.get("comment", ""),
            )
        return Response(ApplicationDetailSerializer(app).data)

    # ── T-3-032: events ──────────────────────────────────────────────────
    @extend_schema(tags=["applications"], summary="Timeline событий заявки",
                   responses=ApplicationEventSerializer(many=True))
    @action(detail=True, methods=["get"])
    def events(self, request, pk=None):
        app = self.get_object()
        qs = app.events.all().order_by("occurred_at", "id")
        return Response({"results": ApplicationEventSerializer(qs, many=True).data})
