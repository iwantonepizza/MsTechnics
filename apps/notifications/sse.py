"""apps/notifications/sse.py — T-3-041: SSE publisher через Redis Streams."""
import json
from typing import Iterable
import structlog

logger = structlog.get_logger(__name__)


class SSEPublisher:
    STREAM_PREFIX = "sse:user:"
    MAXLEN = 100

    def __init__(self):
        self._redis = None

    def _get_redis(self):
        if self._redis is None:
            import redis
            from django.conf import settings
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    def publish(self, *, recipient_user_ids: Iterable[int], event_type: str, payload: dict):
        data = json.dumps(payload, default=str)
        r = self._get_redis()
        for uid in recipient_user_ids:
            try:
                r.xadd(
                    name=f"{self.STREAM_PREFIX}{uid}",
                    fields={"event_type": event_type, "data": data},
                    maxlen=self.MAXLEN, approximate=True,
                )
            except Exception as e:
                logger.error("sse_publish_failed", user_id=uid, error=str(e))


sse_publisher = SSEPublisher()
