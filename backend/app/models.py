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
    # Optional operational fields
    last_active: Optional[datetime] = None
    firmware_version: Optional[str] = None
    ota_update_available: bool = False
    ota_firmware_url: Optional[str] = None
    last_update_check: Optional[datetime] = None


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


class InteractionLog(SQLModel, table=True):
    log_id: Optional[int] = Field(default=None, primary_key=True)
    device_id: str = Field(foreign_key="iotdevice.device_id")
    user_id: Optional[int] = None
    action_type: Optional[str] = None  # 'search', 'trending', 'voice_query', 'face_recognized'
    query: Optional[str] = None
    results_count: Optional[int] = None
    response_time_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TTSCache(SQLModel, table=True):
    cache_id: Optional[int] = Field(default=None, primary_key=True)
    # News identifier and content hash used for versioning
    news_id: str = Field(index=True)
    headline_hash: str = Field(index=True)
    # storage backend: 's3' | 'local'
    storage: str = Field(default='local')
    # key for S3 or local relative path/URL
    key_or_path: str
    # Optional absolute or presigned URL (ephemeral; may be None)
    url: Optional[str] = None
    size_bytes: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed_at: Optional[datetime] = None


class UserPreference(SQLModel, table=True):
    preference_id: Optional[int] = Field(default=None, primary_key=True)
    device_id: str = Field(foreign_key="iotdevice.device_id", index=True)
    user_id: Optional[int] = Field(foreign_key="faceuser.user_id", default=None, index=True)
    # Preferences
    language: Optional[str] = Field(default="en")
    region: Optional[str] = Field(default="in")
    categories: Optional[str] = Field(default=None)  # comma-separated, e.g., "technology,sports"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
