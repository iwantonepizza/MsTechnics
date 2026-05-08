"""T-3-041: SSE stream view."""
import time
from django.conf import settings
from django.http import StreamingHttpResponse
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
import structlog

logger = structlog.get_logger(__name__)
HEARTBEAT_INTERVAL = 15
BLOCK_MS = 5000


class SSEStreamView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_authenticators(self):
        # Поддержка ?token= для browser EventSource
        try:
            token = self.request.GET.get("token")
        except AttributeError:
            token = None
        if token:
            return [_QueryTokenAuth()]
        return super().get_authenticators()

    @extend_schema(tags=["events"], summary="SSE поток событий",
                   responses={200: OpenApiResponse(description="text/event-stream")})
    def get(self, request):
        return StreamingHttpResponse(
            self._stream(request),
            content_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    def _stream(self, request):
        user_id = request.user.id
        stream_name = f"sse:user:{user_id}"
        last_id = request.META.get("HTTP_LAST_EVENT_ID", "$")
        last_heartbeat = time.time()
        try:
            import redis
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            while True:
                events = r.xread({stream_name: last_id}, block=BLOCK_MS, count=10)
                if events:
                    for _, messages in events:
                        for msg_id, fields in messages:
                            yield _format_sse(fields["event_type"], fields["data"], msg_id).encode()
                            last_id = msg_id
                if time.time() - last_heartbeat > HEARTBEAT_INTERVAL:
                    yield b": heartbeat\n\n"
                    last_heartbeat = time.time()
        except (GeneratorExit, ConnectionResetError):
            logger.info("sse_disconnected", user_id=user_id)
        except Exception as e:
            logger.error("sse_error", user_id=user_id, error=str(e))


def _format_sse(event_type: str, data: str, event_id: str = None) -> str:
    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event_type}")
    for line in data.splitlines():
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"


class _QueryTokenAuth(JWTAuthentication):
    def authenticate(self, request):
        token = request.GET.get("token")
        if not token:
            return None
        validated = self.get_validated_token(token)
        return self.get_user(validated), validated
