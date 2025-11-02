from fastapi.testclient import TestClient
from app.main import app


def test_preferences_default():
    with TestClient(app) as client:
        reg = client.post('/api/iot/device/register', json={"device_mac": "AA:BB:CC:DD:01:02", "device_name": "PrefDevice"})
        assert reg.status_code == 201
        token = reg.json()['api_token']
        headers = {"Authorization": f"Bearer {token}"}

        # No preferences yet, should return defaults
        r = client.get('/api/iot/preferences/999', headers=headers)
        assert r.status_code == 200
        assert r.json()['language'] == 'en'
        assert r.json()['region'] == 'in'


def test_preferences_set_and_get():
    with TestClient(app) as client:
        reg = client.post('/api/iot/device/register', json={"device_mac": "AA:BB:CC:DD:02:03", "device_name": "PrefDevice2"})
        token = reg.json()['api_token']
        headers = {"Authorization": f"Bearer {token}"}

        # Set preferences
        payload = {"language": "hi", "region": "us", "categories": "technology,sports"}
        r = client.post('/api/iot/preferences/1', json=payload, headers=headers)
        assert r.status_code == 200
        assert r.json()['language'] == 'hi'
        assert r.json()['region'] == 'us'
        assert r.json()['categories'] == 'technology,sports'

        # Get preferences
        r2 = client.get('/api/iot/preferences/1', headers=headers)
        assert r2.status_code == 200
        assert r2.json()['language'] == 'hi'
        assert r2.json()['region'] == 'us'
