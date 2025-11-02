from fastapi.testclient import TestClient
from app.main import app


def test_trending():
    with TestClient(app) as client:
        # register device to obtain token
        reg = client.post('/api/iot/device/register', json={"device_mac": "AA:BB:CC:11:22:33", "device_name": "TestPod"})
        assert reg.status_code == 201
        token = reg.json()['api_token']

        r = client.get('/api/iot/trending?region=in&limit=3', headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert 'data' in data
        assert isinstance(data['data'], list)
        assert len(data['data']) == 3
        item = data['data'][0]
        assert 'headline' in item and 'confidence' in item


def test_search_found():
    with TestClient(app) as client:
        reg = client.post('/api/iot/device/register', json={"device_mac": "AA:BB:CC:44:55:66", "device_name": "TestPod2"})
        token = reg.json()['api_token']
        r = client.get('/api/iot/search?query=battery', headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert len(data['data']) >= 1


def test_search_not_found():
    with TestClient(app) as client:
        reg = client.post('/api/iot/device/register', json={"device_mac": "AA:BB:CC:77:88:99", "device_name": "TestPod3"})
        token = reg.json()['api_token']
        r = client.get('/api/iot/search?query=unicorns', headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert data['data'] == []


def test_trending_unauthorized():
    with TestClient(app) as client:
        r = client.get('/api/iot/trending?region=in&limit=1')
        # missing Bearer token should return 403 from HTTPBearer
        assert r.status_code == 403
