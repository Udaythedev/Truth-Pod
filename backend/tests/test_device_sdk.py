import pytest
import requests
from fastapi.testclient import TestClient

from app.main import app
from device_sdk.client import DeviceClient


def test_register_and_trending_success():
    client = TestClient(app)
    sdk = DeviceClient(base_url=client.base_url, session=client)

    token = sdk.register_device("sdk-test-1")
    assert isinstance(token, str) and len(token) > 0

    trending = sdk.get_trending(token=token, limit=2)
    assert isinstance(trending, dict)
    # endpoint returns data under 'data' key
    assert "data" in trending


def test_trending_requires_valid_token():
    client = TestClient(app)
    sdk = DeviceClient(base_url=client.base_url, session=client)

    # use a wrong token -> should return 401 and raise for status
    with pytest.raises(Exception):
        sdk.get_trending(token="invalid-token-123", limit=1)
