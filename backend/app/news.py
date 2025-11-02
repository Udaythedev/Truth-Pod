import os
from typing import List, Dict, Optional
import httpx
from app.verify import verify_text

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
NEWSAPI_ENDPOINT = "https://newsapi.org/v2"


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
    """Return trending news. If NEWSAPI_KEY is set, fetch top-headlines, otherwise return mock data."""
    if NEWSAPI_KEY:
        try:
            params = {
                "apiKey": NEWSAPI_KEY,
                "country": region,
                "pageSize": limit,
            }
            r = httpx.get(f"{NEWSAPI_ENDPOINT}/top-headlines", params=params, timeout=5.0)
            r.raise_for_status()
            items = r.json().get("articles", [])
            return [_format_newsapi_article(a) for a in items]
        except Exception:
            # on any error fall back to mock
            return _MOCK_NEWS[:limit]
    return _MOCK_NEWS[:limit]


def search_news(query: str, limit: int = 10) -> List[Dict]:
    """Search news. If NEWSAPI_KEY is set, call NewsAPI 'everything' endpoint, otherwise search mock."""
    if NEWSAPI_KEY:
        try:
            params = {"apiKey": NEWSAPI_KEY, "q": query, "pageSize": limit}
            r = httpx.get(f"{NEWSAPI_ENDPOINT}/everything", params=params, timeout=5.0)
            r.raise_for_status()
            items = r.json().get("articles", [])
            return [_format_newsapi_article(a) for a in items]
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
