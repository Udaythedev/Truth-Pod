import time
from fastapi.testclient import TestClient


def test_tts_background_request_and_status(monkeypatch):
    # Mock boto3 client to avoid real S3
    class FakeClient:
        def put_object(self, Bucket, Key, Body, ContentType=None):
            return {'ResponseMetadata': {'HTTPStatusCode': 200}}
        def generate_presigned_url(self, ClientMethod, Params=None, ExpiresIn=3600):
            return f"https://presigned.example/{Params['Key']}?exp={ExpiresIn}"

    def fake_boto3_client(name, **kwargs):
        return FakeClient()

    import boto3
    monkeypatch.setattr(boto3, 'client', fake_boto3_client)

    from app.main import app
    with TestClient(app) as client:
        reg = client.post('/api/iot/device/register', json={"device_mac": "AA:BB:CC:10:20:30", "device_name": "BGDevice"})
        token = reg.json()['api_token']
        headers = {"Authorization": f"Bearer {token}"}

        trending = client.get('/api/iot/trending?region=in&limit=1', headers=headers)
        nid = trending.json()['data'][0]['news_id']

        # request background synthesis
        r = client.post(f'/api/iot/news/{nid}/tts/request', headers=headers)
        assert r.status_code in (202, 200)

        # poll status until ready
        for _ in range(10):
            s = client.get(f'/api/iot/news/{nid}/tts/status', headers=headers)
            assert s.status_code == 200
            st = s.json()['status']
            if st == 'ready':
                assert 'url' in s.json()
                break
            time.sleep(0.05)
        else:
            raise AssertionError('background TTS did not become ready in time')
