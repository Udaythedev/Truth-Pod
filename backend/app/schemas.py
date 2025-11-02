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
