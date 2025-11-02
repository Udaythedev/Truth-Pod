from fastapi.testclient import TestClient
from app.main import app


def test_news_tts_endpoint():
    with TestClient(app) as client:
        reg = client.post('/api/iot/device/register', json={"device_mac": "AA:BB:CC:99:88:77", "device_name": "TTSDevice"})
        assert reg.status_code == 201
        token = reg.json()['api_token']

        # fetch trending to get a news id
        r = client.get('/api/iot/trending?region=in&limit=3', headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()['data']
        assert len(data) > 0
        nid = data[0]['news_id']

        # request TTS for that news id
        r2 = client.get(f'/api/iot/news/{nid}/tts', headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200
        j = r2.json()
        assert 'audio_base64' in j and 'mime_type' in j
        assert j['mime_type'].startswith('audio/')
