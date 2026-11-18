import time
from collections import defaultdict, deque
from threading import Lock
from fastapi import HTTPException, Request, status

from app.core.config import get_settings


class RateLimiter:
    """Sliding-window rate limiter with Redis support and thread-safe in-memory fallback."""

    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()
        self._redis = None
        self._redis_checked = False

    def _get_redis(self):
        if self._redis_checked:
            return self._redis
        self._redis_checked = True
        settings = get_settings()
        if settings.APP_ENV == "test":
            return None
        try:
            import redis

            client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
            client.ping()
            self._redis = client
        except Exception:
            self._redis = None
        return self._redis

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        settings = get_settings()
        if not settings.RATE_LIMIT_ENABLED:
            return

        r = self._get_redis()
        now = time.time()
        if r is not None:
            try:
                pipe = r.pipeline()
                redis_key = f"rl:{key}"
                pipe.zremrangebyscore(redis_key, 0, now - window_seconds)
                pipe.zadd(redis_key, {f"{now}:{time.monotonic_ns()}": now})
                pipe.zcard(redis_key)
                pipe.expire(redis_key, window_seconds + 1)
                _, _, count, _ = pipe.execute()
                if count > limit:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many requests. Please try again later.",
                    )
                return
            except HTTPException:
                raise
            except Exception:
                pass

        with self._lock:
            dq = self._buckets[key]
            cutoff = now - window_seconds
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                )
            dq.append(now)

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


rate_limiter = RateLimiter()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_dependency(scope: str, limit: int, window_seconds: int):
    def _dep(request: Request) -> None:
        key = f"{scope}:{client_ip(request)}"
        rate_limiter.check(key, limit=limit, window_seconds=window_seconds)

    return _dep
