from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status as http_status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, mixins

from apps.workflow.departures.models import Departure, DepartureStatus, Executor
from apps.activity.services import activity_logger
from shared.exceptions import DomainError
from shared.permissions import HasDepartmentAccess
from shared.throttling import TransitionRateThrottle
from .serializers import (
    DepartureListSerializer, DepartureCreateSerializer,
    DeparturePatchSerializer, DepartureCompleteSerializer, ExecutorSerializer,
)


class ExecutorViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ExecutorSerializer

    def get_queryset(self):
        return Executor.objects.all().order_by("last_name", "first_name", "id")

    @extend_schema(tags=["departures"], summary="Список исполнителей")
    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)

    @extend_schema(tags=["departures"], summary="Детали исполнителя")
    def retrieve(self, *args, **kwargs):
        return super().retrieve(*args, **kwargs)


class DepartureViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin,
    mixins.CreateModelMixin, mixins.UpdateModelMixin,
    mixins.DestroyModelMixin, GenericViewSet
):
    permission_classes = [IsAuthenticated]
    serializer_class = DepartureListSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = Departure.objects.select_related("status", "executor").order_by("-time_updated")
        params = self.request.query_params
        if st := params.get("status"):
            qs = qs.filter(status__name=st)
        user = self.request.user
        if user.permission not in ("admin", "all") and user.allowed_city.exists():
            qs = qs.filter(display__city__in=user.allowed_city.all()).distinct()
        return qs

    def get_permissions(self):
        if self.action in ("create", "partial_update", "complete", "archive", "destroy"):
            return [HasDepartmentAccess.for_("control", "service", "admin", "all")()]
        return [IsAuthenticated()]

    @extend_schema(tags=["departures"], summary="Список выездов",
                   parameters=[OpenApiParameter("status", str)])
    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)

    @extend_schema(tags=["departures"], summary="Детали выезда")
    def retrieve(self, *args, **kwargs):
        return super().retrieve(*args, **kwargs)

    @extend_schema(tags=["departures"], summary="Создать выезд", request=DepartureCreateSerializer)
    def create(self, request, *args, **kwargs):
        s = DepartureCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        executor = Executor.objects.get(id=s.validated_data["executor_id"]) if s.validated_data.get("executor_id") else None
        created_status = DepartureStatus.objects.filter(name="created").first()
        dep = Departure.objects.create(
            description=s.validated_data["description"],
            executor=executor,
            time_start=s.validated_data.get("time_start"),
            status=created_status,
            user_create=request.user.username,
            time_created=timezone.now(),
            time_updated=timezone.now(),
        )
        activity_logger.log(event_type="departure.created", target=dep, actor=request.user,
                             description=f"Создан выезд #{dep.id}")
        try:
            from apps.notifications.triggers.departure import notify_departure_assigned

            notify_departure_assigned(dep)
        except Exception:
            pass
        return Response(DepartureListSerializer(dep).data, status=http_status.HTTP_201_CREATED)

    @extend_schema(tags=["departures"], summary="Обновить выезд", request=DeparturePatchSerializer)
    def partial_update(self, request, *args, **kwargs):
        dep = self.get_object()
        s = DeparturePatchSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        for field in ("description", "time_start"):
            if field in s.validated_data:
                setattr(dep, field, s.validated_data[field])
        if "executor_id" in s.validated_data:
            dep.executor_id = s.validated_data["executor_id"]
        dep.time_updated = timezone.now()
        dep.save()
        return Response(DepartureListSerializer(dep).data)

    @extend_schema(tags=["departures"], summary="Завершить выезд",
                   request=DepartureCompleteSerializer)
    @action(detail=True, methods=["post"], throttle_classes=[TransitionRateThrottle])
    def complete(self, request, pk=None):
        dep = self.get_object()
        s = DepartureCompleteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        completed = DepartureStatus.objects.filter(name="completed").first()
        if not completed:
            raise DomainError("Статус 'completed' не найден в справочнике", code="status_not_found")
        dep.status = completed
        dep.time_end = s.validated_data.get("time_end") or timezone.now()
        dep.time_updated = timezone.now()
        dep.save()
        activity_logger.log(event_type="departure.completed", target=dep, actor=request.user,
                             description=f"Выезд #{dep.id} завершён",
                             comment=s.validated_data.get("comment", ""))
        return Response(DepartureListSerializer(dep).data)

    @extend_schema(tags=["departures"], summary="Архивировать выезд", request=None)
    @action(detail=True, methods=["post"], throttle_classes=[TransitionRateThrottle])
    def archive(self, request, pk=None):
        dep = self.get_object()
        archived = DepartureStatus.objects.filter(name="archived").first()
        dep.status = archived
        dep.time_updated = timezone.now()
        dep.save()
        activity_logger.log(event_type="departure.archived", target=dep, actor=request.user,
                             description=f"Выезд #{dep.id} архивирован")
        return Response(DepartureListSerializer(dep).data)

    @extend_schema(tags=["departures"], summary="Удалить выезд")
    def destroy(self, request, *args, **kwargs):
        dep = self.get_object()
        if dep.status and dep.status.name != "created":
            raise DomainError("Удалить можно только выезд в статусе created",
                               code="delete_not_allowed")
        return super().destroy(request, *args, **kwargs)
