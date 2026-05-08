"""T-3-011/012: ViewSets справочников."""
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet

from apps.core.references.models import Color, Cities, Smile, Condition
from apps.core.references.models import Department
from apps.workflow.applications.models import ApplicationStatus
from apps.workflow.departures.models import DepartureStatus
from shared.permissions import IsAdmin
from .serializers import (
    CitySerializer, ColorSerializer, ConditionSerializer,
    SmileSerializer, DepartmentSerializer, ApplicationStatusSerializer, DepartureStatusSerializer,
)


@extend_schema_view(
    list=extend_schema(tags=["refs"], summary="Список городов"),
    retrieve=extend_schema(tags=["refs"], summary="Город"),
)
class CityViewSet(ReadOnlyModelViewSet):
    serializer_class = CitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.permission in ("admin", "all"):
            return Cities.objects.all().order_by("name")
        return user.allowed_city.all().order_by("name")


@extend_schema_view(
    list=extend_schema(tags=["refs"], summary="Список цветов"),
    retrieve=extend_schema(tags=["refs"], summary="Цвет"),
    create=extend_schema(tags=["refs"], summary="Создать цвет"),
    partial_update=extend_schema(tags=["refs"], summary="Обновить цвет"),
    destroy=extend_schema(tags=["refs"], summary="Удалить цвет"),
)
class ColorViewSet(ModelViewSet):
    queryset = Color.objects.all().order_by("name")
    serializer_class = ColorSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAdmin()]

    def perform_destroy(self, instance):
        in_use = (
            Condition.objects.filter(color=instance).exists()
            or Condition.objects.filter(color_text=instance).exists()
            or ApplicationStatus.objects.filter(color=instance).exists()
        )
        if in_use:
            from shared.exceptions import DomainError
            raise DomainError("Цвет используется в условиях/статусах", code="color_in_use")
        instance.delete()


@extend_schema_view(
    list=extend_schema(tags=["refs"], summary="Состояния панелей"),
    retrieve=extend_schema(tags=["refs"], summary="Состояние"),
)
class ConditionViewSet(ReadOnlyModelViewSet):
    queryset = Condition.objects.select_related("color", "icon").order_by("name")
    serializer_class = ConditionSerializer
    permission_classes = [IsAuthenticated]


@extend_schema_view(
    list=extend_schema(tags=["refs"], summary="Иконки"),
    retrieve=extend_schema(tags=["refs"], summary="Иконка"),
)
class SmileViewSet(ReadOnlyModelViewSet):
    queryset = Smile.objects.all()
    serializer_class = SmileSerializer
    permission_classes = [IsAuthenticated]


@extend_schema_view(
    list=extend_schema(tags=["refs"], summary="Отделы"),
    retrieve=extend_schema(tags=["refs"], summary="Отдел"),
)
class DepartmentViewSet(ReadOnlyModelViewSet):
    queryset = Department.objects.all().order_by("name")
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]


@extend_schema_view(
    list=extend_schema(tags=["refs"], summary="Статусы заявок"),
    retrieve=extend_schema(tags=["refs"], summary="Статус заявки"),
)
class ApplicationStatusViewSet(ReadOnlyModelViewSet):
    queryset = ApplicationStatus.objects.select_related("color", "color_text", "icon").order_by("id")
    serializer_class = ApplicationStatusSerializer
    permission_classes = [IsAuthenticated]


@extend_schema_view(
    list=extend_schema(tags=["refs"], summary="Статусы выездов"),
    retrieve=extend_schema(tags=["refs"], summary="Статус выезда"),
)
class DepartureStatusViewSet(ReadOnlyModelViewSet):
    queryset = DepartureStatus.objects.all().order_by("id")
    serializer_class = DepartureStatusSerializer
    permission_classes = [IsAuthenticated]
