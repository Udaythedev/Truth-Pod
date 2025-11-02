from typing import Optional, Dict, Any
import httpx


class AsyncDeviceClient:
    """Async Device SDK using httpx.AsyncClient.

    Accepts an existing httpx.AsyncClient (with app= for testing) or creates one.
    """

    def __init__(self, base_url: str = "http://localhost:8000", session: Optional[httpx.AsyncClient] = None):
        # Accept URL objects or strings
        self.base_url = str(base_url).rstrip("/")
        self._own_session = session is None
        self.session = session or httpx.AsyncClient(base_url=self.base_url)

    async def aclose(self) -> None:
        if self._own_session:
            await self.session.aclose()

    async def register_device(self, device_id: str, device_type: str = "python-async-sdk") -> str:
        payload = {"device_id": device_id, "device_type": device_type}
        r = await self.session.post(f"{self.base_url}/api/iot/device/register", json=payload)
        r.raise_for_status()
        data = r.json()
        return data["access_token"]

    async def get_trending(self, token: str, limit: int = 10) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"}
        params = {"limit": limit}
        r = await self.session.get(f"{self.base_url}/api/iot/trending", headers=headers, params=params)
        r.raise_for_status()
        return r.json()

    async def search(self, token: str, q: str, limit: int = 10) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"}
        params = {"q": q, "limit": limit}
        r = await self.session.get(f"{self.base_url}/api/iot/search", headers=headers, params=params)
        r.raise_for_status()
        return r.json()

    async def enroll_face(self, token: str, user_id: str, image_b64: str, meta: Optional[Dict] = None) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"user_id": user_id, "image_b64": image_b64, "meta": meta or {}}
        r = await self.session.post(f"{self.base_url}/api/iot/face/enroll", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()

    async def recognize_face(self, token: str, image_b64: str, limit: int = 5) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"image_b64": image_b64, "limit": limit}
        r = await self.session.post(f"{self.base_url}/api/iot/face/recognize", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()
