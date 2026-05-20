from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status as http_status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.core.users.permissions import is_admin
from apps.directory.displays.models import Display
from apps.directory.panels.models import Panel
from shared.permissions import HasCityAccess, HasDepartmentAccess

from .serializers import (
    AlarmEventSerializer,
    DisplayDetailSerializer,
    DisplayListSerializer,
    PhotoUploadSerializer,
)


@extend_schema_view(
    list=extend_schema(
        tags=["displays"],
        summary="Список экранов",
        parameters=[OpenApiParameter("city", str, description="Slug города")],
    ),
    retrieve=extend_schema(tags=["displays"], summary="Детали экрана"),
)
class DisplayViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, HasCityAccess]
    lookup_field = "slug"

    def get_queryset(self):
        qs = Display.objects.select_related("city")
        if self.action == "list":
            panel_queryset = Panel.objects.select_related("condition__color", "condition__icon")
            qs = qs.prefetch_related(Prefetch("cell_set__panel", queryset=panel_queryset))
        user = self.request.user
        if not is_admin(user) and user.allowed_city.exists():
            qs = qs.filter(city__in=user.allowed_city.all())
        if city_slug := self.request.query_params.get("city"):
            qs = qs.filter(city__slug=city_slug)
        return qs.order_by("city__name", "name")

    def get_serializer_class(self):
        return DisplayDetailSerializer if self.action == "retrieve" else DisplayListSerializer

    @extend_schema(tags=["displays"], summary="Контакты экрана")
    @action(detail=True, methods=["get"])
    def contacts(self, _request, slug=None):
        del slug
        from apps.interface.api.v1.departures.serializers import ContactSerializer
        from apps.workflow.departures.models import Contact

        display = self.get_object()
        qs = Contact.objects.filter(displays=display).order_by("last_name")
        return Response(ContactSerializer(qs, many=True).data)

    @extend_schema(
        tags=["displays"],
        summary="VNNOX-алармы экрана",
        parameters=[OpenApiParameter("resolved", bool, description="true/false")],
        responses=AlarmEventSerializer(many=True),
    )
    @action(detail=True, methods=["get"])
    def alarms(self, request, slug=None):
        del slug
        from apps.integrations.gmail_alarms.models import AlarmEvent

        display = self.get_object()
        qs = (
            AlarmEvent.objects.filter(display=display)
            .select_related("cell", "panel")
            .order_by("-occurred_at", "-id")
        )
        resolved = request.query_params.get("resolved")
        if resolved == "false":
            qs = qs.filter(resolved_at__isnull=True)
        elif resolved == "true":
            qs = qs.filter(resolved_at__isnull=False)
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(AlarmEventSerializer(page, many=True).data)
        return Response(AlarmEventSerializer(qs[:200], many=True).data)

    @extend_schema(tags=["displays"], summary="Фотографии экрана")
    @action(detail=True, methods=["get"])
    def photos(self, _request, slug=None):
        del slug
        display = self.get_object()
        photos = display.photos.all().order_by("-id") if hasattr(display, "photos") else []
        return Response(
            [
                {
                    "id": p.id,
                    "url": p.image.url if p.image else None,
                    "uploaded_at": getattr(p, "uploaded_at", None),
                }
                for p in photos
            ]
        )

    @extend_schema(
        tags=["displays"],
        summary="Загрузить фото",
        request={"multipart/form-data": PhotoUploadSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="photos/upload",
        parser_classes=[MultiPartParser, FormParser],
        permission_classes=[IsAuthenticated, HasDepartmentAccess.for_("control", "admin")],
    )
    def upload_photo(self, request, slug=None):
        del slug
        display = self.get_object()
        s = PhotoUploadSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        from apps.directory.displays.models import PhotoDisplay

        photo = PhotoDisplay.objects.create(display=display, image=s.validated_data["file"])
        return Response(
            {"id": photo.id, "url": photo.image.url}, status=http_status.HTTP_201_CREATED
        )
