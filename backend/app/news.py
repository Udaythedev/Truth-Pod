import os
from typing import List, Dict, Optional
import httpx
import hashlib
from app.verify import verify_text

try:
    import redis  # type: ignore
except Exception:
    redis = None

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
NEWSAPI_ENDPOINT = "https://newsapi.org/v2"

# Default news source: 'reddit' preferred for higher public rate limits
# Options: 'reddit' | 'newsapi' | 'mock'
NEWS_SOURCE = os.getenv("NEWS_SOURCE", "reddit").lower()

# Redis for caching
REDIS_URL = os.getenv("REDIS_URL", "")
_redis_client = None
if REDIS_URL and redis is not None:
    try:
        _redis_client = redis.from_url(REDIS_URL)
    except Exception:
        _redis_client = None


# Local fallback mock news
_MOCK_NEWS: List[Dict] = [
    {
        "news_id": "1",
        "headline": "Local school wins national science fair",
        "source": "Daily News",
        "confidence": 0.98,
        "url": "https://example.com/article/1"
    },
    {
        "news_id": "2",
        "headline": "New community garden opens downtown",
        "source": "City Times",
        "confidence": 0.95,
        "url": "https://example.com/article/2"
    },
    {
        "news_id": "3",
        "headline": "Breakthrough in battery technology announced",
        "source": "TechWire",
        "confidence": 0.88,
        "url": "https://example.com/article/3"
    },
    {
        "news_id": "4",
        "headline": "Sports team clinches playoff berth",
        "source": "Sports Daily",
        "confidence": 0.92,
        "url": "https://example.com/article/4"
    },
]


def _in_pytest() -> bool:
    # Avoid real network during unit tests
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


def _format_reddit_post(p: Dict, source_sub: str) -> Dict:
    data = p.get("data", {})
    title = data.get("title") or ""
    url = data.get("url") or ("https://www.reddit.com" + (data.get("permalink") or ""))
    # Use Reddit post id as news_id
    nid = data.get("id") or (url[:32])
    conf = verify_text(title)
    return {
        "news_id": str(nid),
        "headline": title,
        "source": f"Reddit: {source_sub}",
        "confidence": conf,
        "url": url,
    }


def _reddit_headers() -> Dict[str, str]:
    # Reddit requires a descriptive User-Agent
    ua = os.getenv("REDDIT_USER_AGENT", "TruthPod/1.0 (news fetch; contact: support@example.com)")
    return {"User-Agent": ua}


def _reddit_trending(limit: int = 5, timeout: float = 5.0) -> List[Dict]:
    """Fetch top posts from r/news and r/worldnews (last day), combine and trim to limit."""
    subs = ["news", "worldnews"]
    items: List[Dict] = []
    with httpx.Client(timeout=timeout, headers=_reddit_headers()) as client:
        for sub in subs:
            try:
                r = client.get(f"https://www.reddit.com/r/{sub}/top.json", params={"limit": limit, "t": "day"})
                r.raise_for_status()
                children = (r.json().get("data", {}) or {}).get("children", [])
                for c in children:
                    items.append(_format_reddit_post(c, f"r/{sub}"))
            except Exception:
                continue
    # de-duplicate by news_id while preserving order
    seen = set()
    dedup: List[Dict] = []
    for it in items:
        nid = it.get("news_id")
        if nid in seen:
            continue
        seen.add(nid)
        dedup.append(it)
        if len(dedup) >= limit:
            break
    return dedup


def _reddit_search(query: str, limit: int = 10, timeout: float = 5.0) -> List[Dict]:
    """Search Reddit posts by query across r/news and r/worldnews."""
    q = f"(subreddit:news OR subreddit:worldnews) {query}"
    try:
        r = httpx.get(
            "https://www.reddit.com/search.json",
            params={"q": q, "limit": limit, "sort": "top", "t": "week"},
            headers=_reddit_headers(),
            timeout=timeout,
        )
        r.raise_for_status()
        children = (r.json().get("data", {}) or {}).get("children", [])
        out = []
        for c in children:
            # choose subreddit label from post data if available
            sub = "r/" + ((c.get("data") or {}).get("subreddit") or "news")
            out.append(_format_reddit_post(c, sub))
        return out[:limit]
    except Exception:
        return []


def _format_newsapi_article(a: Dict) -> Dict:
    headline = a.get("title") or ""
    conf = verify_text(headline)
    return {
        "news_id": a.get("url", "")[:32],
        "headline": headline,
        "source": (a.get("source") or {}).get("name") if isinstance(a.get("source"), dict) else a.get("source"),
        "confidence": conf,
        "url": a.get("url")
    }


def get_trending(region: Optional[str] = "in", limit: int = 5) -> List[Dict]:
    """Return trending news.

    Priority:
    1) Reddit (default)
    2) NewsAPI (if key present)
    3) Local mock

    Caches results in Redis with key trending:{region}:latest for 5 minutes.
    """
    cache_key = f"trending:{region}:latest"
    
    # Try cache first
    if _redis_client:
        try:
            cached = _redis_client.get(cache_key)
            if cached:
                import json
                return json.loads(cached)[:limit]
        except Exception:
            pass
    
    # Avoid network during tests
    if _in_pytest():
        return _MOCK_NEWS[:limit]

    # Preferred: Reddit
    if NEWS_SOURCE == "reddit":
        try:
            results = _reddit_trending(limit=limit)
            if results:
                if _redis_client:
                    try:
                        import json
                        _redis_client.set(cache_key, json.dumps(results), ex=300)
                    except Exception:
                        pass
                return results
        except Exception:
            pass

    # Next: NewsAPI
    if NEWSAPI_KEY and NEWS_SOURCE in ("newsapi", "reddit", "mock"):
        try:
            params = {
                "apiKey": NEWSAPI_KEY,
                "country": region,
                "pageSize": limit,
            }
            r = httpx.get(f"{NEWSAPI_ENDPOINT}/top-headlines", params=params, timeout=5.0)
            r.raise_for_status()
            items = r.json().get("articles", [])
            results = [_format_newsapi_article(a) for a in items]
            
            # Cache for 5 minutes
            if _redis_client:
                try:
                    import json
                    _redis_client.set(cache_key, json.dumps(results), ex=300)
                except Exception:
                    pass
            
            return results
        except Exception:
            # on any error fall back to mock
            return _MOCK_NEWS[:limit]
    return _MOCK_NEWS[:limit]


def search_news(query: str, limit: int = 10) -> List[Dict]:
    """Search news.

    Priority:
    1) Reddit search (default)
    2) NewsAPI 'everything' (if key present)
    3) Local mock substring search

    Caches results in Redis with key search:{hash(query)} for 30 minutes.
    """
    query_hash = hashlib.sha256(query.encode('utf-8')).hexdigest()[:16]
    cache_key = f"search:{query_hash}"
    
    # Try cache first
    if _redis_client:
        try:
            cached = _redis_client.get(cache_key)
            if cached:
                import json
                return json.loads(cached)[:limit]
        except Exception:
            pass
    
    # Avoid network during tests
    if _in_pytest():
        results = [n for n in _MOCK_NEWS if query.lower() in n["headline"].lower()][:limit]
        for r in results:
            r["confidence"] = verify_text(r.get("headline", ""))
        return results

    # Preferred: Reddit
    if NEWS_SOURCE == "reddit":
        try:
            results = _reddit_search(query, limit=limit)
            if results:
                if _redis_client:
                    try:
                        import json
                        _redis_client.set(cache_key, json.dumps(results), ex=1800)
                    except Exception:
                        pass
                return results
        except Exception:
            pass

    # Next: NewsAPI
    if NEWSAPI_KEY and NEWS_SOURCE in ("newsapi", "reddit", "mock"):
        try:
            params = {"apiKey": NEWSAPI_KEY, "q": query, "pageSize": limit}
            r = httpx.get(f"{NEWSAPI_ENDPOINT}/everything", params=params, timeout=5.0)
            r.raise_for_status()
            items = r.json().get("articles", [])
            results = [_format_newsapi_article(a) for a in items]
            
            # Cache for 30 minutes
            if _redis_client:
                try:
                    import json
                    _redis_client.set(cache_key, json.dumps(results), ex=1800)
                except Exception:
                    pass
            
            return results
        except Exception:
            results = [n for n in _MOCK_NEWS if query.lower() in n["headline"].lower()][:limit]
            # apply verification
            for r in results:
                r["confidence"] = verify_text(r.get("headline", ""))
            return results

    results = [n for n in _MOCK_NEWS if query.lower() in n["headline"].lower()][:limit]
    for r in results:
        r["confidence"] = verify_text(r.get("headline", ""))
    return results
