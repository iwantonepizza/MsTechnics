"""T-4-011: Dashboard summary endpoint."""

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.users.permissions import is_admin


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["dashboard"], summary="Сводка для главного меню")
    def get(self, request):
        user = request.user
        admin_access = is_admin(user)
        from apps.workflow.applications.models import Application

        qs = Application.objects.select_related(
            "status",
            "status__color",
            "status__color_text",
            "status__icon",
            "display",
            "display__city",
            "panel",
            "cell",
        )
        if not admin_access:
            qs = qs.filter(display__city__in=user.allowed_city.all())

        all_active = qs.exclude(status__name__in=["archive_done", "archive_unable"])
        counts = {
            "active_total": all_active.count(),
            "sent_to_control": all_active.filter(status__name="sent_to_control").count(),
            "apply_in_control": all_active.filter(status__name="apply_in_control").count(),
            "sent_to_service": all_active.filter(status__name="sent_to_service").count(),
            "work_in_service": all_active.filter(status__name="work_in_service").count(),
            "done": all_active.filter(status__name="done").count(),
            "unable": all_active.filter(status__name="unable").count(),
        }

        def recent(status_names, limit=5):
            from apps.interface.api.v1.applications.serializers import ApplicationListItemSerializer

            apps = qs.filter(status__name__in=status_names).order_by("-last_update_date_time")[
                :limit
            ]
            return ApplicationListItemSerializer(apps, many=True).data

        return Response(
            {
                "counts": counts,
                "monitoring": {"recent": recent(["sent_to_control"])},
                "control": {"queue": recent(["sent_to_control", "apply_in_control"])},
                "service": {"mine": recent(["sent_to_service", "work_in_service"])},
            }
        )
