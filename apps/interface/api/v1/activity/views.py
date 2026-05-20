from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.activity.models import ActivityLog
from apps.core.users.permissions import is_admin

from .serializers import ActivityLogSerializer


class ActivityLogViewSet(ReadOnlyModelViewSet):
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ActivityLog.objects.select_related("target_type").order_by("-occurred_at", "-id")
        params = self.request.query_params
        if kind := params.get("kind"):
            qs = qs.filter(event_type__startswith=kind)
        if since := params.get("since"):
            qs = qs.filter(occurred_at__gte=since)
        if before := params.get("before"):
            qs = qs.filter(occurred_at__lt=before)
        if actor := params.get("actor"):
            qs = qs.filter(actor_name=actor)
        if display_slug := params.get("display"):
            from django.contrib.contenttypes.models import ContentType
            from django.db.models import Q

            from apps.directory.displays.models import Display
            from apps.directory.panels.models import Panel
            from apps.workflow.applications.models import Application
            d = Display.objects.filter(slug=display_slug).first()
            if not d:
                return qs.none()
            ct_d = ContentType.objects.get_for_model(Display)
            ct_p = ContentType.objects.get_for_model(Panel)
            ct_a = ContentType.objects.get_for_model(Application)
            panel_ids = list(Panel.objects.filter(display=d).values_list("id", flat=True))
            app_ids = list(Application.objects.filter(display=d).values_list("id", flat=True))
            qs = qs.filter(
                Q(target_type=ct_d, target_id=d.id) |
                Q(target_type=ct_p, target_id__in=panel_ids) |
                Q(target_type=ct_a, target_id__in=app_ids)
            )
            return qs
        user = self.request.user
        if not is_admin(user):
            return qs.none()  # без display фильтра — только admin
        return qs

    @extend_schema(tags=["activity"], summary="Журнал активности",
                   parameters=[OpenApiParameter("display", str), OpenApiParameter("kind", str),
                                OpenApiParameter("since", str), OpenApiParameter("before", str)])
    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)

    @extend_schema(tags=["activity"], summary="Запись журнала")
    def retrieve(self, *args, **kwargs):
        return super().retrieve(*args, **kwargs)
