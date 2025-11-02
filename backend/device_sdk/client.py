from typing import Optional, Dict, Any
import requests


class DeviceClient:
    """Minimal Device SDK client for TruthPod backend.

    Uses a requests-like session (FastAPI TestClient is accepted in tests).
    """

    def __init__(self, base_url: str = "http://localhost:8000", session: Optional[requests.Session] = None):
        # Accept URL objects (from TestClient) or strings
        self.base_url = str(base_url).rstrip("/")
        self.session = session or requests.Session()

    def register_device(self, device_mac: str, device_name: Optional[str] = None, device_type: str = "python-sdk") -> str:
        # Align with backend DeviceRegisterRequest fields: device_mac, device_name, device_type
        payload = {"device_mac": device_mac, "device_name": device_name or device_mac, "device_type": device_type}
        r = self.session.post(f"{self.base_url}/api/iot/device/register", json=payload)
        r.raise_for_status()
        data = r.json()
        # backend returns `api_token` in the DeviceRegisterResponse
        return data.get("api_token") or data.get("access_token")

    def get_trending(self, token: str, limit: int = 10) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"}
        params = {"limit": limit}
        r = self.session.get(f"{self.base_url}/api/iot/trending", headers=headers, params=params)
        r.raise_for_status()
        return r.json()

    def search(self, token: str, q: str, limit: int = 10) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"}
        params = {"q": q, "limit": limit}
        r = self.session.get(f"{self.base_url}/api/iot/search", headers=headers, params=params)
        r.raise_for_status()
        return r.json()

    def enroll_face(self, token: str, user_id: str, image_b64: str, meta: Optional[Dict] = None) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"user_id": user_id, "image_b64": image_b64, "meta": meta or {}}
        r = self.session.post(f"{self.base_url}/api/iot/face/enroll", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()

    def recognize_face(self, token: str, image_b64: str, limit: int = 5) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"image_b64": image_b64, "limit": limit}
        r = self.session.post(f"{self.base_url}/api/iot/face/recognize", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()
