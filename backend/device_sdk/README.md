# TruthPod Device SDK (Python)

Minimal SDK to interact with the TruthPod FastAPI backend for device flows.

Usage example:

```python
from device_sdk import DeviceClient
from fastapi.testclient import TestClient
from app.main import app

# In tests you can reuse TestClient as the session
client = TestClient(app)
sdk = DeviceClient(base_url=client.base_url, session=client)

token = sdk.register_device("my-device-1")
print("device token:", token)

trending = sdk.get_trending(token=token)
print(trending)
```

The SDK uses a requests-like session. You can pass a regular `requests.Session()` for real usage
or `fastapi.testclient.TestClient` in tests so calls are routed to the app instance.

## Async usage

If you prefer an async client, the SDK includes `AsyncDeviceClient` which uses `httpx.AsyncClient`.
In tests you can pass `httpx.AsyncClient(app=app)` so requests are routed directly to the FastAPI app:

```python
import asyncio
import httpx
from device_sdk.async_client import AsyncDeviceClient
from app.main import app

async def main():
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        sdk = AsyncDeviceClient(base_url=ac.base_url, session=ac)

        token = await sdk.register_device("my-async-device-1")
        print("device token:", token)

        trending = await sdk.get_trending(token)
        print(trending)

asyncio.run(main())
```

The async client mirrors the sync API (register_device, get_trending, search, enroll_face, recognize_face).
