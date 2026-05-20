# ruff: noqa: RUF002
"""T-7-011: inbox-эндпоинт уведомлений для колокольчика в хедере.

Read-state хранится **на клиенте** (last_seen_id в localStorage), чтобы избежать
BC-breaking миграции на модели Notification. Сервер только отдаёт последние N
уведомлений текущего юзера.
"""

from collections import defaultdict

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.directory.panels.models import Panel
from apps.notifications.models import Notification
from apps.workflow.applications.models import Application
from apps.workflow.departures.models import Departure

from .serializers import NotificationInboxItemSerializer

MAX_LIMIT = 50
DEFAULT_LIMIT = 20


def _parse_target_id(raw_value: str | None) -> int | None:
    if not raw_value:
        return None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _build_deep_link_targets(notifications: list[Notification]) -> dict[tuple[str, str], object]:
    ids_by_kind: dict[str, set[int]] = defaultdict(set)
    for notification in notifications:
        kind = notification.related_target_ct.model if notification.related_target_ct else None
        target_id = _parse_target_id(notification.related_target_id)
        if kind in {"application", "departure", "panel"} and target_id is not None:
            ids_by_kind[kind].add(target_id)

    targets: dict[tuple[str, str], object] = {}

    for application in Application.objects.filter(id__in=ids_by_kind["application"]).select_related(
        "display__city"
    ):
        targets[("application", str(application.id))] = application

    for departure in Departure.objects.filter(id__in=ids_by_kind["departure"]):
        targets[("departure", str(departure.id))] = departure

    for panel in Panel.objects.filter(id__in=ids_by_kind["panel"]).select_related("display"):
        targets[("panel", str(panel.id))] = panel

    return targets


class NotificationInboxView(APIView):
    """GET /api/v1/notifications/inbox/?limit=20

    Возвращает последние N уведомлений для `request.user` со статусом `sent` или
    `pending`. Сортировка по `-created_at`. Юзер видит только свои.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["notifications"],
        summary="Inbox уведомлений текущего юзера (T-7-011)",
        parameters=[OpenApiParameter("limit", int, required=False)],
        responses=NotificationInboxItemSerializer(many=True),
    )
    def get(self, request):
        try:
            limit = int(request.query_params.get("limit", DEFAULT_LIMIT))
        except (TypeError, ValueError):
            limit = DEFAULT_LIMIT
        limit = max(1, min(limit, MAX_LIMIT))

        qs = (
            Notification.objects.filter(recipient=request.user)
            .filter(status__in=[Notification.Status.SENT, Notification.Status.PENDING])
            .select_related("recipient", "related_target_ct")
            .order_by("-created_at")[:limit]
        )
        notifications = list(qs)
        data = NotificationInboxItemSerializer(
            notifications,
            many=True,
            context={"deep_link_targets": _build_deep_link_targets(notifications)},
        ).data
        return Response({"results": data, "count": len(data)})
