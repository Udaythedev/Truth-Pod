import os
import httpx
import hashlib
import json
import re
from typing import Optional

try:
    import redis
except Exception:
    redis = None

# Configuration: external verification providers (Gemini-like or Vertex AI)
GEMINI_API_URL = os.getenv("GEMINI_API_URL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Vertex / Google-style endpoint (optional). Examples:
# - full endpoint: https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT/locations/LOCATION/models/MODEL:predict
# - or a custom proxy URL. Provide VERTEX_API_KEY for API-key auth or set authorization headers in the endpoint.
VERTEX_API_ENDPOINT = os.getenv("VERTEX_API_ENDPOINT", "")
VERTEX_API_KEY = os.getenv("VERTEX_API_KEY", "")

# Redis cache config (optional)
REDIS_URL = os.getenv("REDIS_URL", "")
VERIFY_CACHE_TTL = int(os.getenv("VERIFY_CACHE_TTL_SECONDS", "86400"))  # default 24 hours

_redis_client = None
if REDIS_URL and redis is not None:
    try:
        _redis_client = redis.from_url(REDIS_URL)
    except Exception:
        _redis_client = None


def _mock_verify(text: str) -> float:
    """Simple heuristic-based mock verifier.

    Returns a confidence between 0.0 and 1.0.
    """
    t = text.lower()
    if any(k in t for k in ("breakthrough", "wins", "won", "clinches", "announced", "opens")):
        return 0.92
    if any(k in t for k in ("suspected", "alleged", "rumor", "rumours")):
        return 0.25
    if len(t) < 20:
        return 0.6
    return 0.75


def _extract_confidence_from_response(data) -> Optional[float]:
    """Try several common response shapes to extract a numeric confidence.

    This is intentionally permissive to support different providers (Vertex, Gemini proxies, etc.).
    """
    if not data:
        return None
    # direct key
    if isinstance(data, dict):
        for key in ("confidence", "score", "probability", "prob"):
            v = data.get(key)
            if isinstance(v, (int, float)):
                return float(v)

        # nested: candidates -> first -> confidence
        c = data.get("candidates") or data.get("predictions") or data.get("results")
        if isinstance(c, list) and c:
            first = c[0]
            if isinstance(first, dict):
                for key in ("confidence", "score", "probability", "prob"):
                    v = first.get(key)
                    if isinstance(v, (int, float)):
                        return float(v)
                # sometimes the provider returns text; try to extract a float from it
                text_fields = []
                for tf in ("output", "text", "content", "response"):
                    if tf in first:
                        val = first.get(tf)
                        if isinstance(val, str):
                            text_fields.append(val)
                for t in text_fields:
                    m = re.search(r"([01]?\.\d{1,4}|1\.0|0)", t)
                    if m:
                        try:
                            return float(m.group(1))
                        except Exception:
                            pass

    # fallback: try to find a float in top-level JSON stringification
    try:
        s = json.dumps(data)
        m = re.search(r"([01]?\.\d{1,4}|1\.0|0)", s)
        if m:
            return float(m.group(1))
    except Exception:
        pass

    return None


def verify_text(text: str, timeout: float = 5.0) -> float:
    """Verify a piece of text using Gemini-like API if configured, otherwise fallback to mock.

    Expected external API contract (not enforced): POST GEMINI_API_URL with JSON {"input": text}
    and receive JSON {"confidence": 0.91}.
    """
    # Try cache first
    cache_key = "verify:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    if _redis_client:
        try:
            cached = _redis_client.get(cache_key)
            if cached:
                # stored as JSON string like b"0.92"
                try:
                    return float(cached)
                except Exception:
                    pass
        except Exception:
            # ignore cache errors
            pass

    # Call Vertex-like endpoint if configured
    if VERTEX_API_ENDPOINT and VERTEX_API_KEY:
        try:
            headers = {"Content-Type": "application/json"}
            # prefer API key as query param if provided; some Vertex endpoints support ?key=
            url = VERTEX_API_ENDPOINT
            if VERTEX_API_KEY:
                # if the endpoint already contains a querystring, append, else add
                sep = '&' if '?' in url else '?'
                url = f"{url}{sep}key={VERTEX_API_KEY}"
            payload = {"input": text}
            r = httpx.post(url, json=payload, headers=headers, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            conf = _extract_confidence_from_response(data)
            if conf is not None:
                conf = max(0.0, min(1.0, float(conf)))
                if _redis_client:
                    try:
                        _redis_client.set(cache_key, str(conf), ex=VERIFY_CACHE_TTL)
                    except Exception:
                        pass
                return conf
        except Exception:
            # fall through to next provider/mocks
            pass

    # Call external Gemini-like API if configured
    if GEMINI_API_URL and GEMINI_API_KEY:
        try:
            headers = {"Authorization": f"Bearer {GEMINI_API_KEY}", "Content-Type": "application/json"}
            payload = {"input": text}
            r = httpx.post(GEMINI_API_URL, json=payload, headers=headers, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            conf = _extract_confidence_from_response(data)
            if conf is not None:
                conf = max(0.0, min(1.0, float(conf)))
                # cache result
                if _redis_client:
                    try:
                        _redis_client.set(cache_key, str(conf), ex=VERIFY_CACHE_TTL)
                    except Exception:
                        pass
                return conf
        except Exception:
            # fall through to mock on any error
            pass

    # Fallback to mock verifier
    conf = _mock_verify(text)
    if _redis_client:
        try:
            _redis_client.set(cache_key, str(conf), ex=VERIFY_CACHE_TTL)
        except Exception:
            pass
    return conf
