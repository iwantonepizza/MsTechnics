from rest_framework import serializers

from apps.notifications.models import Notification


def _resolve_department(permission: str | None) -> str:
    if permission in {"monitoring", "control", "service"}:
        return permission
    return "control"


class NotificationInboxItemSerializer(serializers.ModelSerializer):
    """T-7-011: компактный item для колокольчика в хедере.

    Только нужные поля — id, текст, дата создания, контекст-target (kind+id для deeplink).
    """

    target_kind = serializers.SerializerMethodField()
    target_id = serializers.SerializerMethodField()
    deep_link_path = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "rendered_text",
            "created_at",
            "status",
            "delivered_via",
            "target_kind",
            "target_id",
            "deep_link_path",
        ]

    def get_target_kind(self, obj: Notification) -> str | None:
        return obj.related_target_ct.model if obj.related_target_ct else None

    def get_target_id(self, obj: Notification) -> str | None:
        return obj.related_target_id

    def get_deep_link_path(self, obj: Notification) -> str | None:
        kind = self.get_target_kind(obj)
        target_id = self.get_target_id(obj)
        if not kind or not target_id:
            return None

        target = self.context.get("deep_link_targets", {}).get((kind, target_id))
        if target is None:
            return None

        if kind == "application":
            display = getattr(target, "display", None)
            city = getattr(display, "city", None)
            department = _resolve_department(getattr(obj.recipient, "permission", None))
            if display and display.slug and city and city.slug:
                return f"/{department}/{city.slug}/{display.slug}?app_id={target.id}"
            return f"/{department}?app_id={target.id}"

        if kind == "departure":
            return f"/departures?departure_id={target.id}"

        if kind == "panel":
            display = getattr(target, "display", None)
            if display and display.slug:
                return f"/zip/{display.slug}?panel_id={target.id}"
            return f"/zip?panel_id={target.id}#panel-{target.id}"

        return None
