from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.exceptions import DomainError

from .serializers import GlobalSearchResponseSerializer
from .services import GlobalSearchService


class GlobalSearchView(APIView):
    permission_classes = [IsAuthenticated]
    service_class = GlobalSearchService

    @extend_schema(
        tags=["search"],
        summary="Глобальный поиск по 6 категориям",
        parameters=[
            OpenApiParameter("q", str, required=True, description="Поисковый запрос, минимум 2 символа"),
            OpenApiParameter("limit", int, required=False, description="Лимит на категорию, максимум 20"),
        ],
        responses=GlobalSearchResponseSerializer,
    )
    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        if len(query) < 2:
            raise DomainError(
                "Поисковый запрос должен содержать минимум 2 символа.",
                code="search_query_too_short",
            )

        raw_limit = request.query_params.get("limit", "10")
        try:
            limit = min(max(int(raw_limit), 1), 20)
        except ValueError as exc:
            raise DomainError("Параметр limit должен быть целым числом.", code="invalid_limit") from exc

        service = self.service_class()
        payload = service.search(query, limit=limit, user=request.user)
        serializer = GlobalSearchResponseSerializer(payload)
        return Response(serializer.data)
