import os
from fastapi.testclient import TestClient


def test_tts_cache_list_and_delete(monkeypatch):
    # Mock S3
    class FakeClient:
        def put_object(self, Bucket, Key, Body, ContentType=None):
            return {'ResponseMetadata': {'HTTPStatusCode': 200}}
        def generate_presigned_url(self, ClientMethod, Params=None, ExpiresIn=3600):
            return f"https://presigned.example/{Params['Key']}?exp={ExpiresIn}"
        def delete_object(self, Bucket, Key):
            return {'ResponseMetadata': {'HTTPStatusCode': 204}}

    def fake_boto3_client(name, **kwargs):
        return FakeClient()

    monkeypatch.setenv('S3_BUCKET_NAME', 'test-bucket')
    import boto3
    monkeypatch.setattr(boto3, 'client', fake_boto3_client)

    from app.main import app
    with TestClient(app) as client:
        reg = client.post('/api/iot/device/register', json={"device_mac": "AA:BB:CC:70:80:90", "device_name": "CacheDevice"})
        token = reg.json()['api_token']
        headers = {"Authorization": f"Bearer {token}"}

        # Generate a TTS URL (will also record cache)
        trending = client.get('/api/iot/trending?region=in&limit=1', headers=headers)
        nid = trending.json()['data'][0]['news_id']
        r = client.get(f'/api/iot/news/{nid}/tts/url', headers=headers)
        assert r.status_code == 200

        # List cache
        r2 = client.get(f'/api/iot/tts/cache?news_id={nid}', headers=headers)
        assert r2.status_code == 200
        data = r2.json()['data']
        assert len(data) >= 1
        cache_id = data[0]['cache_id']

        # Delete cache
        r3 = client.delete(f'/api/iot/tts/cache/{cache_id}', headers=headers)
        assert r3.status_code == 200
        assert r3.json().get('deleted') is True
