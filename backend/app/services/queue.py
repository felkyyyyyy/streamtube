import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TranscodeQueue:
    """Redis-backed queue for asynchronous video transcoding jobs."""

    def __init__(self) -> None:
        self._redis = None

    def _client(self):
        if self._redis is None:
            import redis

            settings = get_settings()
            self._redis = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        return self._redis

    def enqueue(self, video_id: str) -> bool:
        settings = get_settings()
        if not settings.ENABLE_BACKGROUND_WORKER:
            return False
        try:
            self._client().rpush(settings.TRANSCODE_QUEUE_NAME, video_id)
            return True
        except Exception as exc:
            logger.warning("Failed to enqueue video %s to Redis: %s", video_id, exc)
            return False

    def pop_blocking(self, timeout: int = 5) -> str | None:
        settings = get_settings()
        item = self._client().blpop(settings.TRANSCODE_QUEUE_NAME, timeout=timeout)
        if not item:
            return None
        _, raw_val = item
        return raw_val.decode("utf-8") if isinstance(raw_val, bytes) else str(raw_val)

    def healthcheck(self) -> bool:
        try:
            return bool(self._client().ping())
        except Exception:
            return False


transcode_queue = TranscodeQueue()
