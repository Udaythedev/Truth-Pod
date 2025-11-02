import os
from fastapi.testclient import TestClient
from app import main


class FakeRedis:
    def __init__(self):
        self.store = {}
    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True
    def get(self, key):
        return self.store.get(key)
    def delete(self, key):
        if key in self.store:
            del self.store[key]
            return 1
        return 0


def test_background_tts_with_redis(monkeypatch):
    # Simulate Redis being configured and available
    os.environ["REDIS_URL"] = "redis://fake/0"
    # swap the redis client instance used by the module to our fake
    monkeypatch.setattr(main, "_redis_client", FakeRedis())

    with TestClient(main.app) as client:
        reg = client.post('/api/iot/device/register', json={"device_mac": "00:11:22:33:44:55", "device_name": "RedisDev"})
        assert reg.status_code == 201
        token = reg.json()['api_token']
        headers = {"Authorization": f"Bearer {token}"}

        r = client.get('/api/iot/trending?region=in&limit=1', headers=headers)
        assert r.status_code == 200
        data = r.json()['data']
        assert len(data) > 0
        nid = data[0]['news_id']

        # Request background synth
        req = client.post(f'/api/iot/news/{nid}/tts/request', headers=headers)
        assert req.status_code in (202, 200)

        # Poll until ready (should be quick)
        for _ in range(10):
            s = client.get(f'/api/iot/news/{nid}/tts/status', headers=headers)
            assert s.status_code == 200
            st = s.json()['status']
            if st == 'ready':
                break
        else:
            raise AssertionError("TTS did not become ready in time")
