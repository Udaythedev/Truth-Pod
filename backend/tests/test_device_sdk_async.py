import pytest
import httpx

from app.main import app
from device_sdk.async_client import AsyncDeviceClient


@pytest.mark.asyncio
async def test_async_register_and_trending(monkeypatch):
    sdk = AsyncDeviceClient(base_url="http://test")

    async def fake_register(device_id, device_type="python-async-sdk"):
        return 'async-tok-1'

    async def fake_get_trending(token, limit=10):
        return {'results': [{'id': 'n1'}]}

    monkeypatch.setattr(AsyncDeviceClient, 'register_device', lambda self, device_id, device_type='python-async-sdk': fake_register(device_id, device_type))
    monkeypatch.setattr(AsyncDeviceClient, 'get_trending', lambda self, token, limit=10: fake_get_trending(token, limit))

    token = await sdk.register_device('async-sdk-1')
    assert isinstance(token, str) and len(token) > 0

    trending = await sdk.get_trending(token=token, limit=2)
    assert isinstance(trending, dict)
    assert 'results' in trending


@pytest.mark.asyncio
async def test_async_trending_requires_valid_token(monkeypatch):
    sdk = AsyncDeviceClient(base_url="http://test")

    async def fake_get_trending(token, limit=10):
        raise Exception('unauthorized')

    monkeypatch.setattr(AsyncDeviceClient, 'get_trending', lambda self, token, limit=10: fake_get_trending(token, limit))

    try:
        await sdk.get_trending(token='bad-token-xyz', limit=1)
        assert False, 'expected exception'
    except Exception:
        pass
