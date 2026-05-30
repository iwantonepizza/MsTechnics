from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view
from rest_framework import status as http_status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
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

    def get_permissions(self):
        if self.action == "photos" and self.request.method == "POST":
            return [IsAuthenticated(), HasDepartmentAccess.for_("service", "admin")()]
        if self.action in {"upload_photo", "delete_photo"}:
            return [IsAuthenticated(), HasDepartmentAccess.for_("service", "admin")()]
        return [permission() for permission in self.permission_classes]

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

    @extend_schema(tags=["displays"], summary="Заметки об экране")
    @action(detail=True, methods=["get", "post"])
    def notes(self, request, slug=None):
        del slug
        from apps.activity.services import activity_logger
        from apps.directory.displays.models import DisplayNote

        from .serializers import DisplayNoteSerializer

        display = self.get_object()
        if request.method == "GET":
            qs = DisplayNote.objects.filter(display=display).order_by("-created_at", "-id")
            return Response(DisplayNoteSerializer(qs, many=True).data)

        s = DisplayNoteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = request.user
        author_name = getattr(user, "full_name", None) or user.get_username()
        department = getattr(user, "permission", "") or ""
        note = DisplayNote.objects.create(
            display=display,
            author=user,
            author_name=author_name,
            department=department,
            text=s.validated_data["text"],
        )
        activity_logger.log(
            actor=user,
            target=display,
            event_type="display.note_added",
            description=f"Заметка к экрану {display.name}",
            comment=note.text[:200],
        )
        return Response(
            DisplayNoteSerializer(note).data, status=http_status.HTTP_201_CREATED
        )

    @extend_schema(tags=["displays"], summary="Фотографии экрана")
    @action(detail=True, methods=["get", "post"], parser_classes=[MultiPartParser, FormParser])
    def photos(self, request, slug=None):
        del slug
        display = self.get_object()
        if request.method == "GET":
            photos = display.photos.all().order_by("-id") if hasattr(display, "photos") else []
            return Response(
                [
                    {
                        "id": photo.id,
                        "url": photo.image.url if photo.image else None,
                        "uploaded_at": getattr(photo, "uploaded_at", None),
                    }
                    for photo in photos
                ]
            )
        return self._create_photo(request, display)

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
        return self._create_photo(request, display)

    def _create_photo(self, request, display):
        s = PhotoUploadSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        from apps.directory.displays.models import PhotoDisplay

        photo = PhotoDisplay.objects.create(display=display, image=s.validated_data["file"])
        return Response(
            {
                "id": photo.id,
                "url": photo.image.url,
                "uploaded_at": getattr(photo, "uploaded_at", None),
            },
            status=http_status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=["displays"],
        summary="РЈРґР°Р»РёС‚СЊ С„РѕС‚Рѕ СЌРєСЂР°РЅР°",
        parameters=[OpenApiParameter("photo_id", OpenApiTypes.INT, OpenApiParameter.PATH)],
    )
    @action(
        detail=True,
        methods=["delete"],
        url_path=r"photos/(?P<photo_id>[^/.]+)",
    )
    def delete_photo(self, _request, slug=None, photo_id=None):
        del slug
        display = self.get_object()
        from apps.directory.displays.models import PhotoDisplay

        try:
            photo = PhotoDisplay.objects.get(id=photo_id, display=display)
        except PhotoDisplay.DoesNotExist as exc:
            raise NotFound("Р¤РѕС‚Рѕ РЅРµ РЅР°Р№РґРµРЅРѕ.") from exc
        photo.delete()
        return Response(status=http_status.HTTP_204_NO_CONTENT)
