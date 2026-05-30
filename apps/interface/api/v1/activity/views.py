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
        # T-8-062: точный набор типов событий (через запятую), напр. ?event_types=panel_move,panel.removed
        if event_types := params.get("event_types"):
            names = [name.strip() for name in event_types.split(",") if name.strip()]
            if names:
                qs = qs.filter(event_type__in=names)
        if since := params.get("since"):
            qs = qs.filter(occurred_at__gte=since)
        if before := params.get("before"):
            qs = qs.filter(occurred_at__lt=before)
        if actor := params.get("actor"):
            qs = qs.filter(actor_name=actor)
        if display_slug := params.get("display"):
            return self._filter_by_display(qs, display_slug)
        # T-8-004: история конкретной панели
        if panel_id := params.get("panel"):
            return self._filter_by_panel(qs, panel_id)
        # T-8-004: история «места» (ячейки)
        if cell_id := params.get("cell"):
            return self._filter_by_cell(qs, cell_id)
        user = self.request.user
        if is_admin(user):
            return qs
        # T-8-020: общая лента доступных событий, если у пользователя включён тумблер
        if getattr(user, "show_activity_feed", False):
            return self._filter_by_user_scope(qs, user)
        return qs.none()  # без фильтра и без тумблера — только admin

    # ─── helpers ────────────────────────────────────────────────────────────

    def _content_types(self):
        from django.contrib.contenttypes.models import ContentType

        from apps.directory.displays.models import Display
        from apps.directory.panels.models import Panel
        from apps.workflow.applications.models import Application

        return {
            "display": ContentType.objects.get_for_model(Display),
            "panel": ContentType.objects.get_for_model(Panel),
            "application": ContentType.objects.get_for_model(Application),
        }

    def _filter_by_display(self, qs, display_slug):
        from django.db.models import Q

        from apps.directory.displays.models import Display
        from apps.directory.panels.models import Panel
        from apps.workflow.applications.models import Application

        d = Display.objects.filter(slug=display_slug).first()
        if not d:
            return qs.none()
        ct = self._content_types()
        panel_ids = list(Panel.objects.filter(display=d).values_list("id", flat=True))
        app_ids = list(Application.objects.filter(display=d).values_list("id", flat=True))
        return qs.filter(
            Q(target_type=ct["display"], target_id=d.id)
            | Q(target_type=ct["panel"], target_id__in=panel_ids)
            | Q(target_type=ct["application"], target_id__in=app_ids)
        )

    def _filter_by_panel(self, qs, panel_id):
        """История панели: события самой панели + события её заявок."""
        from django.db.models import Q

        from apps.directory.panels.models import Panel
        from apps.workflow.applications.models import Application

        panel = Panel.objects.filter(id=panel_id).first()
        if not panel:
            return qs.none()
        ct = self._content_types()
        app_ids = list(Application.objects.filter(panel=panel).values_list("id", flat=True))
        return qs.filter(
            Q(target_type=ct["panel"], target_id=panel.id)
            | Q(target_type=ct["application"], target_id__in=app_ids)
        )

    def _filter_by_cell(self, qs, cell_id):
        """История «места»: события установки/снятия панелей в этой ячейке."""
        from django.db.models import Q

        from apps.directory.displays.models import Cell

        cell = Cell.objects.filter(id=cell_id).select_related("display").first()
        if not cell:
            return qs.none()
        ct = self._content_types()
        # panel.removed пишет payload.from_cell_id; display_panel_replace — cell_position на target=display
        return qs.filter(
            Q(payload__from_cell_id=cell.id)
            | Q(
                target_type=ct["display"],
                target_id=cell.display_id,
                payload__cell_position=cell.position,
            )
        )

    def _filter_by_user_scope(self, qs, user):
        """T-8-020: лента событий по экранам/панелям/заявкам доступных пользователю городов."""
        from django.db.models import Q

        from apps.directory.displays.models import Display
        from apps.directory.panels.models import Panel
        from apps.workflow.applications.models import Application

        if not user.allowed_city.exists():
            return qs  # нет ограничений по городам — видит всё
        display_ids = list(
            Display.objects.filter(city__in=user.allowed_city.all()).values_list("id", flat=True)
        )
        ct = self._content_types()
        panel_ids = list(
            Panel.objects.filter(display_id__in=display_ids).values_list("id", flat=True)
        )
        app_ids = list(
            Application.objects.filter(display_id__in=display_ids).values_list("id", flat=True)
        )
        return qs.filter(
            Q(target_type=ct["display"], target_id__in=display_ids)
            | Q(target_type=ct["panel"], target_id__in=panel_ids)
            | Q(target_type=ct["application"], target_id__in=app_ids)
        )

    @extend_schema(
        tags=["activity"],
        summary="Журнал активности",
        parameters=[
            OpenApiParameter("display", str),
            OpenApiParameter("panel", int),
            OpenApiParameter("cell", int),
            OpenApiParameter("kind", str),
            OpenApiParameter("event_types", str, description="CSV точных event_type"),
            OpenApiParameter("since", str),
            OpenApiParameter("before", str),
        ],
    )
    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)

    @extend_schema(tags=["activity"], summary="Запись журнала")
    def retrieve(self, *args, **kwargs):
        return super().retrieve(*args, **kwargs)
