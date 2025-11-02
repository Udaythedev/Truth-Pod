import os
import time
from typing import Callable, Optional
from fastapi import Request, Depends

try:
    import redis  # type: ignore
except Exception:
    redis = None

REDIS_URL = os.getenv("REDIS_URL", "")
_rate_redis = None
if REDIS_URL and redis is not None:
    try:
        _rate_redis = redis.from_url(REDIS_URL)
    except Exception:
        _rate_redis = None

def _rate_enabled() -> bool:
    return os.getenv("RATE_LIMIT_ENABLED", "0") == "1"


def _ip_from_scope(scope) -> str:
    client = scope.get('client') or (None, None)
    host = client[0] if isinstance(client, (list, tuple)) and client else None
    return host or 'unknown'


def get_rate_limiter(limit: int = 60, window_s: int = 60) -> Callable:
    """Factory returning a dependency that rate limits per-device (if available) and per-IP.

    When RATE_LIMIT_ENABLED != '1', this is a no-op.
    Uses Redis when configured, else in-process token bucket per key.
    """
    buckets = {}

    def _key(device_id: Optional[str], ip: str) -> str:
        if device_id:
            return f"rl:dev:{device_id}:{window_s}"
        return f"rl:ip:{ip}:{window_s}"

    def dependency(request: Request):  # FastAPI will pass Request if declared
        if not _rate_enabled():
            return
        # derive key
        device_id = None
        # We can't import app.auth here to avoid circulars; rely on header when available
        # In practice, endpoints using this dependency already require auth, so you can pass device context
        ip = _ip_from_scope(request.scope)
        key = _key(device_id, ip)
        now = int(time.time())
        window_start = now - (now % window_s)
        key = f"{key}:{window_start}"

        # Redis path
        if _rate_redis:
            try:
                # increment and set expiry to end of window
                count = _rate_redis.incr(key)
                ttl = _rate_redis.ttl(key)
                if ttl == -1:
                    _rate_redis.expire(key, window_s)
                if count > limit:
                    from fastapi import HTTPException
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
                return
            except Exception:
                pass

        # Fallback in-process
        c = buckets.get(key, 0)
        c += 1
        buckets[key] = c
        if c > limit:
            from fastapi import HTTPException
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    return dependency


def rate_limit_for_device(limit: int = 120, window_s: int = 60):
    """Rate limit bound to device_id using auth dependency. No-op unless RATE_LIMIT_ENABLED=1.

    This creates a dependency that itself depends on get_current_device, avoiding circular imports
    by importing inside the factory.
    """
    try:
        from app.auth import get_current_device  # import lazily to avoid circular
        from app.models import IoTDevice  # type: ignore
    except Exception:
        get_current_device = None  # type: ignore

    buckets = {}

    def dependency(request: Request, current_device = Depends(get_current_device) if get_current_device else None):
        if not _rate_enabled():
            return
        device_id = getattr(current_device, 'device_id', None)
        now = int(time.time())
        window_start = now - (now % window_s)
        key = f"rl:dev:{device_id or 'unknown'}:{window_s}:{window_start}"

        if _rate_redis:
            try:
                count = _rate_redis.incr(key)
                ttl = _rate_redis.ttl(key)
                if ttl == -1:
                    _rate_redis.expire(key, window_s)
                if count > limit:
                    from fastapi import HTTPException
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
                return
            except Exception:
                pass

        c = buckets.get(key, 0)
        c += 1
        buckets[key] = c
        if c > limit:
            from fastapi import HTTPException
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    return dependency
