from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid
from sqlalchemy import Column, LargeBinary


class IoTDevice(SQLModel, table=True):
    device_id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    device_mac: str = Field(index=True, nullable=False)
    device_name: Optional[str]
    device_type: Optional[str]
    api_token: Optional[str]
    registered_at: datetime = Field(default_factory=datetime.utcnow)


class FaceUser(SQLModel, table=True):
    user_id: Optional[int] = Field(default=None, primary_key=True)
    device_id: str = Field(foreign_key="iotdevice.device_id")
    user_name: str
    face_embedding: Optional[bytes] = Field(sa_column=Column(LargeBinary))
    face_image_url: Optional[str] = None
    enrollment_date: datetime = Field(default_factory=datetime.utcnow)
    confidence_threshold: float = 0.85
    last_recognized_at: Optional[datetime] = None
    recognition_count: int = 0
