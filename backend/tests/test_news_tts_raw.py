from fastapi.testclient import TestClient
from app.main import app


def test_news_tts_raw_endpoint():
    with TestClient(app) as client:
        reg = client.post('/api/iot/device/register', json={"device_mac": "AA:BB:CC:12:34:56", "device_name": "TTSRawDevice"})
        token = reg.json()['api_token']

        r = client.get('/api/iot/trending?region=in&limit=3', headers={"Authorization": f"Bearer {token}"})
        data = r.json()['data']
        nid = data[0]['news_id']

        r2 = client.get(f'/api/iot/news/{nid}/tts/raw', headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200
        assert r2.headers.get('content-type', '').startswith('audio/')
        content = r2.content
        # WAV files start with 'RIFF'
        assert content[:4] == b'RIFF'
        assert len(content) > 100
