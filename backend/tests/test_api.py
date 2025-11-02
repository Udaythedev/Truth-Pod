from fastapi.testclient import TestClient
from app.main import app


def test_health():
    with TestClient(app) as client:
        r = client.get('/api/health')
        assert r.status_code == 200
        assert r.json().get('status') == 'ok'


def test_device_register():
    payload = {
        "device_mac": "AA:BB:CC:DD:EE:FF",
        "device_name": "TestPod",
        "device_type": "ESP32"
    }
    with TestClient(app) as client:
        r = client.post('/api/iot/device/register', json=payload)
        assert r.status_code == 201
        data = r.json()
        assert 'api_token' in data
        assert 'device_id' in data
