import os
from fastapi import FastAPI, HTTPException, Depends
from app.schemas import DeviceRegisterRequest, DeviceRegisterResponse
from app.database import init_db, engine
from app.models import IoTDevice, FaceUser
from sqlmodel import Session, select
from datetime import datetime
import base64
import hashlib
from app.embeddings import embed_from_image_base64, similarity, face_lib_available
import os
from fastapi import Path
from typing import Optional
from app.schemas import NewsItem, NewsListResponse
from app.auth import create_token, get_current_device
from app.news import get_trending as news_get_trending, search_news as news_search
from app.config import SECRET_KEY, ALGORITHM
import uuid
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB/schema on startup
    init_db()
    yield


app = FastAPI(title="TruthPod - Backend (MVP)", lifespan=lifespan)

# mount static files (media) after app is created
from fastapi.staticfiles import StaticFiles
MEDIA_DIR = os.path.join(os.path.dirname(__file__), '..', 'media')
os.makedirs(MEDIA_DIR, exist_ok=True)
app.mount('/media', StaticFiles(directory=os.path.abspath(MEDIA_DIR)), name='media')

@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.post("/api/iot/device/register", response_model=DeviceRegisterResponse, status_code=201)
def register_device(payload: DeviceRegisterRequest):
    # Basic validation
    if not payload.device_mac:
        raise HTTPException(status_code=400, detail="device_mac is required")

    with Session(engine) as session:
        statement = select(IoTDevice).where(IoTDevice.device_mac == payload.device_mac)
        existing = session.exec(statement).first()
        if existing:
            # Return existing device info (re-issue token)
            token = create_token(existing.device_id)
            existing.api_token = token
            session.add(existing)
            session.commit()
            return DeviceRegisterResponse(device_id=existing.device_id, api_token=token)

        device = IoTDevice(
            device_mac=payload.device_mac,
            device_name=payload.device_name,
            device_type=payload.device_type,
        )
        session.add(device)
        session.commit()
        session.refresh(device)
        token = create_token(device.device_id)
        device.api_token = token
        session.add(device)
        session.commit()
        return DeviceRegisterResponse(device_id=device.device_id, api_token=token)


# --- Mock news data and endpoints (MVP) -------------------------------------------------
_MOCK_NEWS = [
    {
        "news_id": "1",
        "headline": "Local school wins national science fair",
        "source": "Daily News",
        "confidence": 0.98,
        "url": "https://example.com/article/1"
    },
    {
        "news_id": "2",
        "headline": "New community garden opens downtown",
        "source": "City Times",
        "confidence": 0.95,
        "url": "https://example.com/article/2"
    },
    {
        "news_id": "3",
        "headline": "Breakthrough in battery technology announced",
        "source": "TechWire",
        "confidence": 0.88,
        "url": "https://example.com/article/3"
    },
    {
        "news_id": "4",
        "headline": "Sports team clinches playoff berth",
        "source": "Sports Daily",
        "confidence": 0.92,
        "url": "https://example.com/article/4"
    },
]


@app.get("/api/iot/trending", response_model=NewsListResponse)
def get_trending(region: Optional[str] = "in", limit: int = 5, current_device: IoTDevice = Depends(get_current_device)):
    """Return a small list of trending, verified news (mock)."""
    items = news_get_trending(region=region, limit=limit)
    return {"data": items}


@app.get("/api/iot/search", response_model=NewsListResponse)
def search_news(query: str, limit: int = 10, current_device: IoTDevice = Depends(get_current_device)):
    """Search mock news headlines by substring match (case-insensitive)."""
    results = news_search(query=query, limit=limit)
    return {"data": results[:limit]}


# --- Face recognition endpoints ---------------------------------------------------------
def _embed_from_image_base64(b64: str) -> bytes:
    return embed_from_image_base64(b64)


def _similarity(a: bytes, b: bytes) -> float:
    return similarity(a, b)


@app.post("/api/iot/face/enroll")
def face_enroll(payload: dict, current_device: IoTDevice = Depends(get_current_device)):
    """Enroll a face for the current device. payload: {"user_name": str, "image_base64": str}
    Returns created user info.
    """
    user_name = payload.get("user_name")
    image_b64 = payload.get("image_base64")
    if not user_name or not image_b64:
        raise HTTPException(status_code=400, detail="user_name and image_base64 are required")
    embedding = _embed_from_image_base64(image_b64)
    with Session(engine) as session:
        user = FaceUser(device_id=current_device.device_id, user_name=user_name, face_embedding=embedding)
        session.add(user)
        session.commit()
        session.refresh(user)

        # save image to media directory using user id
        filename = f"face_{current_device.device_id}_{user.user_id}.jpg"
        filepath = os.path.join(os.path.abspath(MEDIA_DIR), filename)
        try:
            with open(filepath, 'wb') as f:
                f.write(base64.b64decode(image_b64))
            # store URL path
            url_path = f"/media/{filename}"
            user.face_image_url = url_path
            session.add(user)
            session.commit()
        except Exception:
            # ignore file write errors but continue
            url_path = None

        return {"user_id": user.user_id, "user_name": user.user_name, "face_image_url": url_path}


@app.post("/api/iot/face/recognize")
def face_recognize(payload: dict, current_device: IoTDevice = Depends(get_current_device)):
    """Recognize a face for the current device. payload: {"image_base64": str}
    Returns {"user_id": int, "user_name": str, "confidence": float} or {"user_id": null, "user_name": "UNKNOWN"}
    """
    image_b64 = payload.get("image_base64")
    if not image_b64:
        raise HTTPException(status_code=400, detail="image_base64 is required")
    emb = _embed_from_image_base64(image_b64)
    best = None
    best_sim = 0.0
    with Session(engine) as session:
        statement = select(FaceUser).where(FaceUser.device_id == current_device.device_id)
        for fu in session.exec(statement):
            if not fu.face_embedding:
                continue
            sim = _similarity(emb, fu.face_embedding)
            if sim > best_sim:
                best_sim = sim
                best = fu
        if best and best_sim >= best.confidence_threshold:
            best.recognition_count = (best.recognition_count or 0) + 1
            best.last_recognized_at = datetime.utcnow()
            session.add(best)
            session.commit()
            return {"user_id": best.user_id, "user_name": best.user_name, "confidence": round(best_sim, 3)}
        return {"user_id": None, "user_name": "UNKNOWN", "confidence": round(best_sim, 3)}


@app.get("/api/iot/face/users")
def face_users(current_device: IoTDevice = Depends(get_current_device)):
    with Session(engine) as session:
        statement = select(FaceUser).where(FaceUser.device_id == current_device.device_id)
        rows = [ {"user_id": r.user_id, "user_name": r.user_name} for r in session.exec(statement) ]
        return {"data": rows}


@app.delete("/api/iot/face/user/{user_id}")
def face_delete(user_id: int = Path(..., ge=1), current_device: IoTDevice = Depends(get_current_device)):
    with Session(engine) as session:
        statement = select(FaceUser).where(FaceUser.user_id == user_id, FaceUser.device_id == current_device.device_id)
        user = session.exec(statement).first()
        if not user:
            raise HTTPException(status_code=404, detail="user not found")
        session.delete(user)
        session.commit()
        return {"deleted": True}

