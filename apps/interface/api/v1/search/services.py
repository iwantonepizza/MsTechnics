from __future__ import annotations

from typing import Any

from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Case, FloatField, Q, QuerySet, Value, When
from django.db.models.functions import Coalesce, Greatest
from django.db.utils import DatabaseError

from apps.core.users.models import MsUser
from apps.core.users.permissions import is_admin
from apps.directory.displays.models import Display
from apps.directory.panels.models import Panel
from apps.directory.storage.models import Connectors, Hubs, Lamels, PowerBlocks, Wires
from apps.workflow.applications.models import Application
from apps.workflow.departures.models import Departure


class GlobalSearchService:
    """Aggregates global search results across all searchable entities."""

    STORAGE_MODELS = (
        ("wires", Wires),
        ("hubs", Hubs),
        ("lamels", Lamels),
        ("power-blocks", PowerBlocks),
        ("connectors", Connectors),
    )

    def search(self, query: str, *, limit: int, user: MsUser) -> dict[str, list[dict[str, Any]]]:
        return {
            "displays": self._search_displays(query, limit=limit, user=user),
            "panels": self._search_panels(query, limit=limit, user=user),
            "applications": self._search_applications(query, limit=limit, user=user),
            "departures": self._search_departures(query, limit=limit),
            "users": self._search_users(query, limit=limit, user=user),
            "storage": self._search_storage(query, limit=limit),
        }

    def _search_displays(self, query: str, *, limit: int, user: MsUser) -> list[dict[str, Any]]:
        queryset = Display.objects.select_related("city")
        queryset = self._filter_by_allowed_cities(queryset, user=user, city_lookup="city")
        queryset = self._rank_queryset(
            queryset,
            query=query,
            fields=("name", "description", "slug"),
            limit=limit,
        )
        return [
            {
                "id": display.id,
                "name": display.name,
                "description": display.description,
                "slug": display.slug,
                "city_name": display.city.name,
                "city_slug": display.city.slug,
                "score": float(display.score),
            }
            for display in queryset
        ]

    def _search_panels(self, query: str, *, limit: int, user: MsUser) -> list[dict[str, Any]]:
        queryset = Panel.objects.select_related("display__city", "condition", "department")
        queryset = self._filter_by_allowed_cities(
            queryset,
            user=user,
            city_lookup="display__city",
            include_null_city=True,
        )
        queryset = self._rank_queryset(
            queryset,
            query=query,
            fields=("name", "comment", "display__name", "display__description", "display__slug"),
            limit=limit,
        )
        return [
            {
                "id": panel.id,
                "name": panel.name,
                "display_name": panel.display.description if panel.display else None,
                "display_slug": panel.display.slug if panel.display else None,
                "city_slug": panel.display.city.slug if panel.display else None,
                "condition_name": panel.condition.name if panel.condition else None,
                "department_name": panel.department.name if panel.department else None,
                "active_application_id": panel.active_application.id if panel.active_application else None,
                "score": float(panel.score),
            }
            for panel in queryset
        ]

    def _search_applications(self, query: str, *, limit: int, user: MsUser) -> list[dict[str, Any]]:
        queryset = Application.objects.select_related("display__city", "panel", "cell", "status")
        queryset = self._filter_by_allowed_cities(queryset, user=user, city_lookup="display__city")
        queryset = self._rank_queryset(
            queryset,
            query=query,
            fields=(
                "comment_monitoring",
                "comment_control_apply",
                "comment_control_send",
                "comment_service_apply",
                "comment_control_at_work",
                "comment_control_unable",
                "comment_control_archive",
                "panel__name",
                "display__name",
                "display__description",
                "display__slug",
                "status__name",
                "status__description",
            ),
            limit=limit,
            include_exact_id=True,
        )
        return [
            {
                "id": application.id,
                "display_name": application.display.description if application.display else None,
                "display_slug": application.display.slug if application.display else None,
                "city_slug": application.display.city.slug if application.display else None,
                "panel_name": application.panel.name if application.panel else None,
                "cell_position": application.cell.position if application.cell else None,
                "status_name": application.status.name if application.status else None,
                "initial_comment": application.comment_monitoring,
                "score": float(application.score),
            }
            for application in queryset
        ]

    def _search_departures(self, query: str, *, limit: int) -> list[dict[str, Any]]:
        queryset = Departure.objects.select_related("executor", "status")
        queryset = self._rank_queryset(
            queryset,
            query=query,
            fields=("description", "executor__first_name", "executor__last_name"),
            limit=limit,
            include_exact_id=True,
        )
        return [
            {
                "id": departure.id,
                "description": departure.description,
                "executor_name": self._full_name(
                    departure.executor.first_name if departure.executor else None,
                    departure.executor.last_name if departure.executor else None,
                ),
                "status_name": departure.status.name if departure.status else None,
                "score": float(departure.score),
            }
            for departure in queryset
        ]

    def _search_users(self, query: str, *, limit: int, user: MsUser) -> list[dict[str, Any]]:
        if not is_admin(user):
            return []

        queryset = self._rank_queryset(
            MsUser.objects.all(),
            query=query,
            fields=("username", "first_name", "last_name"),
            limit=limit,
            include_exact_id=True,
        )
        return [
            {
                "id": candidate.id,
                "username": candidate.username,
                "full_name": candidate.full_name,
                "permission": candidate.permission,
                "score": float(candidate.score),
            }
            for candidate in queryset
        ]

    def _search_storage(self, query: str, *, limit: int) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for kind, model in self.STORAGE_MODELS:
            queryset = self._rank_queryset(
                model.objects.all(),
                query=query,
                fields=("name", "description"),
                limit=limit,
            )
            results.extend(
                {
                    "id": item.id,
                    "kind": kind,
                    "name": item.name,
                    "description": item.description,
                    "count": item.count,
                    "score": float(item.score),
                }
                for item in queryset
            )
        return sorted(results, key=lambda item: (-item["score"], item["name"]))[:limit]

    def _rank_queryset(
        self,
        queryset: QuerySet,
        *,
        query: str,
        fields: tuple[str, ...],
        limit: int,
        include_exact_id: bool = False,
    ) -> list[Any]:
        filters = Q()
        for field in fields:
            filters |= Q(**{f"{field}__icontains": query})

        exact_id = self._exact_id_bonus(query) if include_exact_id else Value(0.0)
        if include_exact_id and query.isdigit():
            filters |= Q(id=int(query))

        trigram_score = Greatest(self._similarity_expr(fields, query), exact_id, output_field=FloatField())
        try:
            ranked_queryset = (
                queryset.filter(filters).annotate(score=trigram_score).order_by("-score", "id")[:limit]
            )
            return list(ranked_queryset)
        except DatabaseError:
            fallback_score = Greatest(
                self._fallback_score_expr(fields, query),
                exact_id,
                output_field=FloatField(),
            )
            fallback_queryset = (
                queryset.filter(filters).annotate(score=fallback_score).order_by("-score", "id")[:limit]
            )
            return list(fallback_queryset)

    def _similarity_expr(self, fields: tuple[str, ...], query: str):
        expressions = [
            Coalesce(TrigramSimilarity(field, query), Value(0.0), output_field=FloatField())
            for field in fields
        ]
        if len(expressions) == 1:
            return expressions[0]
        return Greatest(*expressions, output_field=FloatField())

    def _fallback_score_expr(self, fields: tuple[str, ...], query: str):
        expressions = [
            Case(
                When(**{f"{field}__icontains": query}, then=Value(1.0)),
                default=Value(0.0),
                output_field=FloatField(),
            )
            for field in fields
        ]
        if len(expressions) == 1:
            return expressions[0]
        return Greatest(*expressions, output_field=FloatField())

    def _exact_id_bonus(self, query: str):
        if not query.isdigit():
            return Value(0.0)
        return Case(
            When(id=int(query), then=Value(1.2)),
            default=Value(0.0),
            output_field=FloatField(),
        )

    def _filter_by_allowed_cities(
        self,
        queryset: QuerySet,
        *,
        user: MsUser,
        city_lookup: str,
        include_null_city: bool = False,
    ) -> QuerySet:
        if is_admin(user) or not user.allowed_city.exists():
            return queryset

        filters = Q(**{f"{city_lookup}__in": user.allowed_city.all()})
        if include_null_city:
            filters |= Q(**{f"{city_lookup}__isnull": True})
        return queryset.filter(filters)

    def _full_name(self, first_name: str | None, last_name: str | None) -> str | None:
        full_name = f"{first_name or ''} {last_name or ''}".strip()
        return full_name or None
