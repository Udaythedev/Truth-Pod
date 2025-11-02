import os
from fastapi.testclient import TestClient
import types


def test_news_tts_presigned_monkeypatch(monkeypatch):
    # ensure S3 env is set
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'

    # fake boto3 client
    class FakeClient:
        def put_object(self, Bucket, Key, Body, ContentType=None):
            # pretend success
            return {'ResponseMetadata': {'HTTPStatusCode': 200}}

        def generate_presigned_url(self, ClientMethod, Params=None, ExpiresIn=3600):
            return f"https://presigned.example/{Params['Key']}?exp={ExpiresIn}"

    def fake_boto3_client(name, **kwargs):
        return FakeClient()

    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')
    monkeypatch.setattr('boto3.client', fake_boto3_client)

    from app.main import app

    with TestClient(app) as client:
        reg = client.post('/api/iot/device/register', json={"device_mac": "AA:BB:CC:21:43:65", "device_name": "S3Device"})
        token = reg.json()['api_token']

        r = client.get('/api/iot/trending?region=in&limit=3', headers={"Authorization": f"Bearer {token}"})
        nid = r.json()['data'][0]['news_id']

        r2 = client.get(f'/api/iot/news/{nid}/tts/url', headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200
        j = r2.json()
        assert 'url' in j
        assert j['url'].startswith('https://presigned.example/')
