from fastapi.testclient import TestClient
from app.main import app


def test_token_rotation_flow():
    with TestClient(app) as client:
        # Register device
        reg = client.post('/api/iot/device/register', json={"device_mac": "AA:BB:CC:00:11:22", "device_name": "RotateMe"})
        assert reg.status_code == 201
        token1 = reg.json()['api_token']
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Can call a protected endpoint
        r = client.get('/api/iot/trending?limit=1', headers=headers1)
        assert r.status_code == 200

        # Rotate token
        rot = client.post('/api/iot/device/token/rotate', headers=headers1)
        assert rot.status_code == 200
        token2 = rot.json()['api_token']
        assert token2 and token2 != token1

        # Old token should now be rejected
        r_old = client.get('/api/iot/trending?limit=1', headers=headers1)
        assert r_old.status_code == 401

        # New token works
        headers2 = {"Authorization": f"Bearer {token2}"}
        r_new = client.get('/api/iot/trending?limit=1', headers=headers2)
        assert r_new.status_code == 200
