from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import MeSerializer, ChangePasswordSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["me"], summary="Текущий пользователь", responses=MeSerializer)
    def get(self, request):
        return Response(MeSerializer(request.user).data)

    @extend_schema(tags=["me"], summary="Обновить профиль",
                   request=MeSerializer, responses=MeSerializer)
    def patch(self, request):
        s = MeSerializer(request.user, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        fields_to_update = []
        for field in ("email", "telegram_id"):
            if field in s.validated_data:
                setattr(request.user, field, s.validated_data[field])
                fields_to_update.append(field)
        # max_id из source
        if "max_id" in s.validated_data:
            request.user.max_id = s.validated_data["max_id"]
            fields_to_update.append("max_id")
        if fields_to_update:
            request.user.save(update_fields=fields_to_update)
        return Response(MeSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["me"], summary="Сменить пароль",
                   request=ChangePasswordSerializer,
                   responses={204: OpenApiResponse(description="OK"), 422: None})
    def post(self, request):
        s = ChangePasswordSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if not request.user.check_password(s.validated_data["old_password"]):
            return Response(
                {"detail": "Старый пароль неверен", "code": "invalid_password", "errors": None},
                status=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        request.user.set_password(s.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response(status=http_status.HTTP_204_NO_CONTENT)
