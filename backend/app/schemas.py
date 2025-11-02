from pydantic import BaseModel
from typing import Optional

class DeviceRegisterRequest(BaseModel):
    device_mac: str
    device_name: Optional[str] = None
    device_type: Optional[str] = "ESP32"

class DeviceRegisterResponse(BaseModel):
    device_id: str
    api_token: str


class NewsItem(BaseModel):
    news_id: str
    headline: str
    source: Optional[str]
    confidence: float
    url: Optional[str] = None


class NewsListResponse(BaseModel):
    data: list[NewsItem]


class DeviceStatusResponse(BaseModel):
    device_id: str
    device_mac: str
    device_name: Optional[str]
    device_type: Optional[str]
    last_active: Optional[str]
    firmware_version: Optional[str]
    ota_update_available: bool = False
    ota_firmware_url: Optional[str]


class InteractionLogRequest(BaseModel):
    action_type: str
    query: Optional[str] = None
    user_id: Optional[int] = None
    results_count: Optional[int] = None
    response_time_ms: Optional[int] = None


class VoiceTranscribeResponse(BaseModel):
    text: str


class TTSResponse(BaseModel):
    audio_base64: Optional[str]
    mime_type: Optional[str] = "audio/wav"
