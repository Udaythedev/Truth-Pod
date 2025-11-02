import os
from fastapi.testclient import TestClient
from app.main import app


def test_https_enforcement(monkeypatch):
    # Enforce HTTPS
    monkeypatch.setenv('HTTPS_ENFORCE', '1')
    # By default TestClient uses http scheme and no x-forwarded-proto
    with TestClient(app) as client:
        r = client.get('/api/health')
        assert r.status_code == 426
        assert r.json()['detail'].lower().startswith('https required')

        # Simulate proxy header indicating https
        r2 = client.get('/api/health', headers={'x-forwarded-proto': 'https'})
        assert r2.status_code == 200
        assert 'X-Request-ID' in r2.headers
