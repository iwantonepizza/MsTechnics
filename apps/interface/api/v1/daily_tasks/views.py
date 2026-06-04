from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.core.users.permissions import has_role, is_admin
from apps.workflow.daily_tasks.models import DailyTask

from .serializers import DailyTaskSerializer


class DailyTaskViewSet(ReadOnlyModelViewSet):
    """T-8-035: ежедневные задачи. Мониторинг выполняет, контроль смотрит прогресс."""

    serializer_class = DailyTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = DailyTask.objects.select_related("city").order_by("start_time", "name")
        user = self.request.user
        if not is_admin(user) and user.allowed_city.exists():
            qs = qs.filter(city__in=user.allowed_city.all())

        city_id = self.request.query_params.get("city")
        if city_id:
            try:
                city_id = int(city_id)
            except ValueError as exc:
                raise ValidationError({"city": "City id must be an integer."}) from exc
            qs = qs.filter(city_id=city_id)
        return qs

    @extend_schema(
        tags=["daily-tasks"],
        summary="Список ежедневных задач",
        parameters=[OpenApiParameter("city", int, description="ID города")],
    )
    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)

    @extend_schema(tags=["daily-tasks"], summary="Задача")
    def retrieve(self, *args, **kwargs):
        return super().retrieve(*args, **kwargs)

    @extend_schema(
        tags=["daily-tasks"],
        summary="Отметить задачу выполненной (открыл ссылку)",
        request=None,
        responses=DailyTaskSerializer,
    )
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        del pk
        from django.utils import timezone

        from apps.activity.services import activity_logger

        user = request.user
        # T-8-035: выполнять может только мониторинг (контроль — read-only)
        if not (is_admin(user) or has_role(user, "monitoring", "all")):
            raise PermissionDenied("Только мониторинг может выполнять ежедневные задачи.")

        task = self.get_object()
        if not task.check_available_status():
            raise ValidationError(
                {"detail": "Задача недоступна для выполнения (не открыта или уже закрыта)."}
            )

        task.complete_task(timezone.now())
        activity_logger.log(
            actor=user,
            target=task,
            event_type="daily_task_complete",
            description=f"Задача «{task.name}» выполнена",
        )
        return Response(DailyTaskSerializer(task).data)
