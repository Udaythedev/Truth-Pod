import base64
from fastapi.testclient import TestClient
from app.main import app


def _b64(s: bytes) -> str:
    return base64.b64encode(s).decode('ascii')


def test_face_enroll_and_recognize():
    with TestClient(app) as client:
        reg = client.post('/api/iot/device/register', json={"device_mac": "AA:BB:CC:01:02:03", "device_name": "FacePod"})
        assert reg.status_code == 201
        token = reg.json()['api_token']

        # enroll a face (fake image bytes)
        img = b"face-image-1"
        payload = {"user_name": "Alice", "image_base64": _b64(img)}
        r = client.post('/api/iot/face/enroll', json=payload, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert 'user_id' in data
        assert 'face_image_url' in data and data['face_image_url'] is not None
        # check file exists
        import os
        fn = data['face_image_url'].lstrip('/')
        assert os.path.exists(os.path.join(os.path.dirname(__file__), '..', fn))

        # recognize using same image
        r2 = client.post('/api/iot/face/recognize', json={"image_base64": _b64(img)}, headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200
        res = r2.json()
        assert res['user_name'] == 'Alice'


def test_face_not_found():
    with TestClient(app) as client:
        reg = client.post('/api/iot/device/register', json={"device_mac": "AA:BB:CC:04:05:06", "device_name": "FacePod2"})
        token = reg.json()['api_token']
        img = b"some-other-face"
        r = client.post('/api/iot/face/recognize', json={"image_base64": _b64(img)}, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        res = r.json()
        assert res['user_name'] == 'UNKNOWN'
