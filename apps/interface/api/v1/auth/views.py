"""T-3-010 + T-3-fix-002: auth views."""
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status as http_status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.exceptions import InvalidToken
import structlog

from shared.throttling import LoginRateThrottle
from .serializers import LoginRequestSerializer, LoginResponseSerializer, TokenObtainPairSerializer

logger = structlog.get_logger(__name__)
REFRESH_COOKIE = "mstech_refresh"


def _cookie_kwargs():
    lifetime = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
    return dict(
        key=REFRESH_COOKIE, httponly=True,
        secure=not settings.DEBUG, samesite="Lax",
        max_age=int(lifetime), path="/api/v1/auth",
    )


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    @extend_schema(
        tags=["auth"], summary="Вход",
        request=LoginRequestSerializer,
        responses={200: LoginResponseSerializer, 401: None},
    )
    def post(self, request):
        s = LoginRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        ts = TokenObtainPairSerializer(data=s.validated_data)
        try:
            ts.is_valid(raise_exception=True)
        except (AuthenticationFailed, InvalidToken, TokenError):
            return Response(
                {"detail": "Неверные учётные данные", "code": "invalid_credentials", "errors": None},
                status=http_status.HTTP_401_UNAUTHORIZED,
            )

        access = ts.validated_data["access"]
        refresh = ts.validated_data["refresh"]

        logger.info("user_login", username=s.validated_data.get("username"))
        resp = Response({"access": access})
        resp.set_cookie(value=refresh, **_cookie_kwargs())
        return resp


class RefreshView(APIView):
    """
    T-3-fix-002 / B4: Правильная rotation с blacklist старого токена.

    - Читаем refresh из httpOnly cookie
    - Blacklist старый токен (предотвращаем повторное использование)
    - Создаём новый refresh + access для того же юзера
    - Отдаём access в JSON, новый refresh в cookie
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["auth"], summary="Обновить токен",
        request=None,
        responses={200: LoginResponseSerializer, 401: None},
    )
    def post(self, request):
        refresh_str = request.COOKIES.get(REFRESH_COOKIE)
        if not refresh_str:
            return Response(
                {"detail": "Refresh-токен отсутствует", "code": "token_missing", "errors": None},
                status=http_status.HTTP_401_UNAUTHORIZED,
            )

        try:
            old_refresh = RefreshToken(refresh_str)
        except TokenError:
            return Response(
                {"detail": "Refresh-токен недействителен или истёк", "code": "token_expired", "errors": None},
                status=http_status.HTTP_401_UNAUTHORIZED,
            )

        # Blacklist старый токен — предотвращает replay-атаку
        try:
            old_refresh.blacklist()
        except AttributeError:
            # token_blacklist не установлен — игнорируем (dev без blacklist app)
            logger.warning("token_blacklist_unavailable")

        # Создаём новую пару для того же юзера
        from apps.core.users.models import MsUser
        try:
            user = MsUser.objects.get(id=old_refresh["user_id"])
        except MsUser.DoesNotExist:
            return Response(
                {"detail": "Пользователь не найден", "code": "user_not_found", "errors": None},
                status=http_status.HTTP_401_UNAUTHORIZED,
            )

        new_refresh = RefreshToken.for_user(user)
        access = str(new_refresh.access_token)

        resp = Response({"access": access})
        resp.set_cookie(value=str(new_refresh), **_cookie_kwargs())
        return resp


class LogoutView(APIView):
    @extend_schema(
        tags=["auth"], summary="Выход",
        request=None,
        responses={204: OpenApiResponse(description="Успешно")},
    )
    def post(self, request):
        refresh_str = request.COOKIES.get(REFRESH_COOKIE)
        if refresh_str:
            try:
                RefreshToken(refresh_str).blacklist()
            except (TokenError, AttributeError):
                pass  # Токен уже недействителен — это OK

        logger.info("user_logout", user=str(request.user))
        resp = Response(status=http_status.HTTP_204_NO_CONTENT)
        resp.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")
        return resp
