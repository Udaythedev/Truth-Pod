import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi import BackgroundTasks
from app.schemas import DeviceRegisterRequest, DeviceRegisterResponse
from app.database import init_db, engine
from app.models import IoTDevice, FaceUser, TTSCache, UserPreference
from app.models import InteractionLog
from sqlmodel import Session, select
from datetime import datetime
import base64
import hashlib
from app.embeddings import embed_from_image_base64, similarity, face_lib_available
import os
from fastapi import Path
from typing import Optional
from app.schemas import NewsItem, NewsListResponse
from app.schemas import DeviceStatusResponse, InteractionLogRequest, VoiceTranscribeResponse, TTSResponse
from app.auth import create_token, get_current_device
from app.news import get_trending as news_get_trending, search_news as news_search
from app.config import SECRET_KEY, ALGORITHM
import uuid
from contextlib import asynccontextmanager
from fastapi import Request
from fastapi.responses import FileResponse, Response
from app.security import get_rate_limiter, rate_limit_for_device
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import httpx
import json
import struct
from app.voice import transcribe_from_bytes, synthesize_text
try:
    import redis  # optional
except Exception:
    redis = None
    
# Redis config for background TTS pending tracking (optional)
REDIS_URL = os.getenv("REDIS_URL", "")
TTS_PENDING_TTL = int(os.getenv("TTS_PENDING_TTL", "300"))
_redis_client = None
if REDIS_URL and redis is not None:
    try:
        _redis_client = redis.from_url(REDIS_URL)
    except Exception:
        _redis_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB/schema on startup
    init_db()
    yield


app = FastAPI(title="TruthPod - Backend (MVP)", lifespan=lifespan)

# Optional Sentry and Prometheus instrumentation
try:
    import sentry_sdk  # type: ignore
    _dsn = os.getenv("SENTRY_DSN", "")
    if _dsn:
        sentry_sdk.init(dsn=_dsn, traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")))
except Exception:
    pass

try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest  # type: ignore
    HAVE_PROM = True
except Exception:
    HAVE_PROM = False

# mount static files (media) after app is created
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import logging
MEDIA_DIR = os.path.join(os.path.dirname(__file__), '..', 'media')
os.makedirs(MEDIA_DIR, exist_ok=True)
app.mount('/media', StaticFiles(directory=os.path.abspath(MEDIA_DIR)), name='media')

# Basic logging configuration controlled by LOG_LEVEL
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

# CORS (configurable via ALLOW_ORIGINS="*" or comma-separated list)
allow_origins = [o.strip() for o in os.getenv("ALLOW_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Optional /metrics endpoint for Prometheus
if 'HAVE_PROM' in globals() and HAVE_PROM:
    from fastapi import APIRouter
    metrics_router = APIRouter()

    @metrics_router.get("/metrics")
    def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    app.include_router(metrics_router)


# Request ID and HTTPS enforcement middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


@app.middleware("http")
async def https_enforce_middleware(request: Request, call_next):
    # Read env dynamically so tests and runtime toggles are picked up without reload
    if os.getenv("HTTPS_ENFORCE", "0") == "1":
        trust = os.getenv("TRUST_X_FORWARDED_PROTO", "1") == "1"
        proto = request.headers.get("x-forwarded-proto") if trust else None
        scheme = (proto or request.url.scheme or "").lower()
        if scheme != "https":
            return Response(status_code=426, content='{"detail":"HTTPS required"}', media_type="application/json")
    return await call_next(request)

# Background TTS tracking: prefer Redis, fallback to in-memory set
_PENDING_TTS = set()

def _pending_key(safe_id: str, h: str) -> str:
    return f"tts:pending:{safe_id}:{h}"

def _mark_pending(safe_id: str, h: str) -> bool:
    key = _pending_key(safe_id, h)
    if _redis_client:
        try:
            # set if not exists with TTL
            return bool(_redis_client.set(key, "1", ex=TTS_PENDING_TTL, nx=True))
        except Exception:
            pass
    # fallback in-memory
    k = f"{safe_id}:{h}"
    if k in _PENDING_TTS:
        return False
    _PENDING_TTS.add(k)
    return True

def _is_pending(safe_id: str, h: str) -> bool:
    key = _pending_key(safe_id, h)
    if _redis_client:
        try:
            return bool(_redis_client.get(key))
        except Exception:
            pass
    return f"{safe_id}:{h}" in _PENDING_TTS

def _clear_pending(safe_id: str, h: str) -> None:
    key = _pending_key(safe_id, h)
    if _redis_client:
        try:
            _redis_client.delete(key)
            return
        except Exception:
            pass
    _PENDING_TTS.discard(f"{safe_id}:{h}")

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


@app.post("/api/iot/device/token/rotate")
def device_token_rotate(current_device: IoTDevice = Depends(get_current_device)):
    """Rotate the device API token. The old token will be rejected on future requests."""
    with Session(engine) as session:
        dev = session.get(IoTDevice, current_device.device_id)
        if not dev:
            raise HTTPException(status_code=404, detail="device not found")
        token = create_token(dev.device_id)
        dev.api_token = token
        session.add(dev)
        session.commit()
        return {"device_id": dev.device_id, "api_token": token}


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
def get_trending(region: Optional[str] = "in", limit: int = 5, current_device: IoTDevice = Depends(get_current_device), _rl: None = Depends(rate_limit_for_device(limit=120, window_s=60))):
    """Return a small list of trending, verified news (mock)."""
    items = news_get_trending(region=region, limit=limit)
    return {"data": items}


@app.get("/api/iot/search", response_model=NewsListResponse)
def search_news(query: str, limit: int = 10, current_device: IoTDevice = Depends(get_current_device), _rl: None = Depends(rate_limit_for_device(limit=120, window_s=60))):
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
            # optionally upload to Cloudinary if configured
            cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "")
            upload_preset = os.getenv("CLOUDINARY_UPLOAD_PRESET", "")
            if cloud_name and upload_preset:
                try:
                    upload_url = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"
                    with open(filepath, 'rb') as imgf:
                        files = {"file": imgf}
                        data = {"upload_preset": upload_preset}
                        r = httpx.post(upload_url, data=data, files=files, timeout=10.0)
                        if r.status_code == 200:
                            j = r.json()
                            # Cloudinary returns secure_url
                            url = j.get("secure_url") or j.get("url")
                            if url:
                                user.face_image_url = url
                                session.add(user)
                                session.commit()
                except Exception:
                    # ignore cloud upload errors
                    pass
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
            # log interaction asynchronously (best-effort)
            try:
                log = InteractionLog(device_id=current_device.device_id, user_id=best.user_id, action_type="face_recognized", query=None, results_count=1)
                session.add(log)
                session.commit()
            except Exception:
                pass
            return {"user_id": best.user_id, "user_name": best.user_name, "confidence": round(best_sim, 3)}
        return {"user_id": None, "user_name": "UNKNOWN", "confidence": round(best_sim, 3)}


# --- Device heartbeat / status / OTA ----------------------------------------------------
@app.post("/api/iot/device/heartbeat")
def device_heartbeat(payload: dict, current_device: IoTDevice = Depends(get_current_device)):
    """Device sends periodic heartbeat. payload may include firmware_version."""
    fw = payload.get("firmware_version")
    with Session(engine) as session:
        dev = session.get(IoTDevice, current_device.device_id)
        if not dev:
            raise HTTPException(status_code=404, detail="device not found")
        dev.last_active = datetime.utcnow()
        dev.last_update_check = datetime.utcnow()
        if fw:
            dev.firmware_version = fw
        session.add(dev)
        session.commit()
        return {"ok": True, "device_id": dev.device_id}


@app.get("/api/iot/device/status", response_model=DeviceStatusResponse)
def device_status(current_device: IoTDevice = Depends(get_current_device)):
    with Session(engine) as session:
        dev = session.get(IoTDevice, current_device.device_id)
        if not dev:
            raise HTTPException(status_code=404, detail="device not found")
        return DeviceStatusResponse(
            device_id=dev.device_id,
            device_mac=dev.device_mac,
            device_name=dev.device_name,
            device_type=dev.device_type,
            last_active=dev.last_active.isoformat() if dev.last_active else None,
            firmware_version=dev.firmware_version,
            ota_update_available=bool(dev.ota_update_available),
            ota_firmware_url=dev.ota_firmware_url,
        )


# --- OTA: upload firmware and query latest ----------------------------------------------
@app.post("/api/iot/firmware/upload")
def firmware_upload(payload: dict, current_device: IoTDevice = Depends(get_current_device)):
    """Upload a firmware blob (base64) for a given device_type and mark devices as having an update.

    Payload: { "version": "0.1.3", "device_type": "ESP32", "firmware_base64": "..." }
    """
    version = payload.get("version")
    device_type = payload.get("device_type") or "ESP32"
    b64 = payload.get("firmware_base64")
    if not version or not b64:
        raise HTTPException(status_code=400, detail="version and firmware_base64 are required")
    try:
        data = base64.b64decode(b64)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid base64 payload")

    ota_dir = os.path.join(os.path.abspath(MEDIA_DIR), "ota")
    os.makedirs(ota_dir, exist_ok=True)
    filename = f"firmware_{device_type}_{version}.bin"
    filepath = os.path.join(ota_dir, filename)
    try:
        with open(filepath, 'wb') as f:
            f.write(data)
    except Exception:
        raise HTTPException(status_code=500, detail="could not write firmware file")

    url_path = f"/media/ota/{filename}"

    # mark devices of this type as having OTA available
    with Session(engine) as session:
        statement = select(IoTDevice).where(IoTDevice.device_type == device_type)
        for dev in session.exec(statement):
            dev.ota_update_available = True
            dev.ota_firmware_url = url_path
            session.add(dev)
        session.commit()

    return {"ok": True, "version": version, "url": url_path}


@app.get("/api/iot/firmware/latest")
def firmware_latest(device_type: Optional[str] = "ESP32"):
    """Return the latest firmware URL for a device type if available.
    This scans the media/ota directory for matching filenames and returns the highest version found (lexical)."""
    ota_dir = os.path.join(os.path.abspath(MEDIA_DIR), "ota")
    if not os.path.isdir(ota_dir):
        return {"available": False}
    files = [f for f in os.listdir(ota_dir) if f.startswith(f"firmware_{device_type}_")]
    if not files:
        return {"available": False}
    # choose lexically max (versions like 0.1.2 should sort correctly for simple cases)
    latest = sorted(files)[-1]
    return {"available": True, "version": latest.replace(f"firmware_{device_type}_", "").replace('.bin',''), "url": f"/media/ota/{latest}"}


# --- News TTS helper --------------------------------------------------------------
@app.get("/api/iot/news/{news_id}/tts", response_model=TTSResponse)
def news_tts(news_id: str, current_device: IoTDevice = Depends(get_current_device)):
    """Return speech audio for a news item headline (base64 WAV).

    Looks up the news item from the trending list and synthesizes its headline.
    """
    items = news_get_trending(limit=50)
    found = None
    for it in items:
        if str(it.get("news_id")) == str(news_id):
            found = it
            break
    if not found:
        raise HTTPException(status_code=404, detail="news item not found")
    headline = found.get("headline") or ""
    audio_bytes, mime = synthesize_text(headline)
    b64 = base64.b64encode(audio_bytes).decode("ascii")
    return TTSResponse(audio_base64=b64, mime_type=mime)


@app.get("/api/iot/news/{news_id}/tts/raw")
def news_tts_raw(news_id: str, current_device: IoTDevice = Depends(get_current_device)):
    """Return raw WAV bytes for a news headline. Cached on-disk under media/tts/{news_id}.wav."""
    # find news item
    items = news_get_trending(limit=50)
    found = None
    for it in items:
        if str(it.get("news_id")) == str(news_id):
            found = it
            break
    if not found:
        raise HTTPException(status_code=404, detail="news item not found")

    tts_dir = os.path.join(os.path.abspath(MEDIA_DIR), "tts")
    os.makedirs(tts_dir, exist_ok=True)
    safe_id = str(news_id).replace('/', '_')
    # compute a short hash of the headline so we can detect changes and version the cache
    headline = (found.get("headline") or "").strip()
    h = hashlib.sha256(headline.encode('utf-8')).hexdigest()[:8]
    filename = f"news_{safe_id}_{h}.wav"
    filepath = os.path.join(tts_dir, filename)

    if not os.path.isfile(filepath):
        # synthesize and write
        audio_bytes, mime = synthesize_text(headline)
        try:
            # remove old cached files for this news id (cache invalidation)
            for f in os.listdir(tts_dir):
                if f.startswith(f"news_{safe_id}_") and f.endswith('.wav'):
                    try:
                        os.remove(os.path.join(tts_dir, f))
                    except Exception:
                        pass
            with open(filepath, 'wb') as f:
                f.write(audio_bytes)
        except Exception:
            # if write fails, stream bytes directly
            return Response(content=audio_bytes, media_type=mime)

    return FileResponse(filepath, media_type="audio/wav")


@app.post("/api/iot/news/{news_id}/tts/refresh")
def news_tts_refresh(news_id: str, current_device: IoTDevice = Depends(get_current_device)):
    """Force refresh the cached WAV for a news headline by regenerating the audio.

    Useful for admin flows when headlines were updated and we need to regenerate cached audio.
    """
    items = news_get_trending(limit=50)
    found = None
    for it in items:
        if str(it.get("news_id")) == str(news_id):
            found = it
            break
    if not found:
        raise HTTPException(status_code=404, detail="news item not found")

    tts_dir = os.path.join(os.path.abspath(MEDIA_DIR), "tts")
    os.makedirs(tts_dir, exist_ok=True)
    safe_id = str(news_id).replace('/', '_')
    headline = (found.get("headline") or "").strip()
    h = hashlib.sha256(headline.encode('utf-8')).hexdigest()[:8]
    filename = f"news_{safe_id}_{h}.wav"
    filepath = os.path.join(tts_dir, filename)

    # remove any existing cache files for this news id
    for f in os.listdir(tts_dir):
        if f.startswith(f"news_{safe_id}_") and f.endswith('.wav'):
            try:
                os.remove(os.path.join(tts_dir, f))
            except Exception:
                pass

    audio_bytes, mime = synthesize_text(headline)
    try:
        with open(filepath, 'wb') as f:
            f.write(audio_bytes)
    except Exception:
        raise HTTPException(status_code=500, detail="could not write tts cache file")

    return {"ok": True, "path": f"/media/tts/{filename}"}


def _s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION')
    )


def upload_tts_to_s3(key: str, content: bytes, content_type: str = 'audio/wav') -> bool:
    bucket = os.getenv('S3_BUCKET_NAME') or os.getenv('AWS_S3_BUCKET')
    if not bucket:
        return False
    try:
        client = _s3_client()
        client.put_object(Bucket=bucket, Key=key, Body=content, ContentType=content_type)
        return True
    except (BotoCoreError, ClientError):
        return False


def generate_presigned_s3_url(key: str, expires: int = 3600) -> str:
    bucket = os.getenv('S3_BUCKET_NAME') or os.getenv('AWS_S3_BUCKET')
    if not bucket:
        return ''
    client = _s3_client()
    try:
        return client.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': key}, ExpiresIn=expires)
    except (BotoCoreError, ClientError):
        return ''


@app.get("/api/iot/news/{news_id}/tts/url")
def news_tts_presigned(news_id: str, current_device: IoTDevice = Depends(get_current_device)):
    """Return a presigned URL for the synthesized headline audio. If S3 is configured, upload and return a presigned URL.

    Falls back to the local cached file URL if S3 is not configured or upload fails.
    """
    items = news_get_trending(limit=50)
    found = None
    for it in items:
        if str(it.get("news_id")) == str(news_id):
            found = it
            break
    if not found:
        raise HTTPException(status_code=404, detail="news item not found")

    headline = (found.get("headline") or "").strip()
    safe_id = str(news_id).replace('/', '_')
    h = hashlib.sha256(headline.encode('utf-8')).hexdigest()[:8]
    key = f"tts/news_{safe_id}_{h}.wav"

    # synthesize audio
    audio_bytes, mime = synthesize_text(headline)

    # try S3 upload if configured
    bucket = os.getenv('S3_BUCKET_NAME') or os.getenv('AWS_S3_BUCKET')
    if bucket:
        ok = upload_tts_to_s3(key, audio_bytes, content_type='audio/wav')
        if ok:
            url = generate_presigned_s3_url(key, expires=int(os.getenv('TTS_PRESIGNED_EXPIRY', '3600')))
            if url:
                # record cache metadata
                with Session(engine) as session:
                    entry = TTSCache(
                        news_id=safe_id,
                        headline_hash=h,
                        storage='s3',
                        key_or_path=key,
                        url=None,
                        size_bytes=len(audio_bytes),
                        last_accessed_at=datetime.utcnow(),
                    )
                    session.add(entry)
                    session.commit()
                return {"url": url, "expires_in": int(os.getenv('TTS_PRESIGNED_EXPIRY', '3600'))}

    # fallback to local cache path and return media URL
    tts_dir = os.path.join(os.path.abspath(MEDIA_DIR), "tts")
    os.makedirs(tts_dir, exist_ok=True)
    filename = f"news_{safe_id}_{h}.wav"
    filepath = os.path.join(tts_dir, filename)
    try:
        with open(filepath, 'wb') as f:
            f.write(audio_bytes)
        # record local cache metadata
        with Session(engine) as session:
            entry = TTSCache(
                news_id=safe_id,
                headline_hash=h,
                storage='local',
                key_or_path=f"/media/tts/{filename}",
                url=f"/media/tts/{filename}",
                size_bytes=len(audio_bytes),
                last_accessed_at=datetime.utcnow(),
            )
            session.add(entry)
            session.commit()
    except Exception:
        pass

    return {"url": f"/media/tts/{filename}", "expires_in": None}


@app.get("/api/iot/tts/cache")
def tts_cache_list(news_id: Optional[str] = None, current_device: IoTDevice = Depends(get_current_device)):
    """List TTS cache entries. Optionally filter by news_id."""
    with Session(engine) as session:
        q = select(TTSCache)
        if news_id:
            q = q.where(TTSCache.news_id == str(news_id))
        rows = session.exec(q).all()
        out = []
        for r in rows:
            out.append({
                "cache_id": r.cache_id,
                "news_id": r.news_id,
                "headline_hash": r.headline_hash,
                "storage": r.storage,
                "key_or_path": r.key_or_path,
                "size_bytes": r.size_bytes,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "last_accessed_at": r.last_accessed_at.isoformat() if r.last_accessed_at else None,
            })
        return {"data": out}


@app.delete("/api/iot/tts/cache/{cache_id}")
def tts_cache_delete(cache_id: int, current_device: IoTDevice = Depends(get_current_device)):
    """Delete a TTS cache entry and its underlying object when possible."""
    with Session(engine) as session:
        entry = session.get(TTSCache, cache_id)
        if not entry:
            raise HTTPException(status_code=404, detail="cache entry not found")
        # try to delete underlying storage
        if entry.storage == 's3':
            bucket = os.getenv('S3_BUCKET_NAME') or os.getenv('AWS_S3_BUCKET')
            if bucket and entry.key_or_path:
                try:
                    client = _s3_client()
                    client.delete_object(Bucket=bucket, Key=entry.key_or_path)
                except Exception:
                    pass
        elif entry.storage == 'local' and entry.key_or_path:
            # key_or_path might be a URL path like /media/tts/filename.wav
            if entry.key_or_path.startswith('/media/'):
                local_path = os.path.join(os.path.abspath(MEDIA_DIR), entry.key_or_path.replace('/media/', ''))
            else:
                local_path = entry.key_or_path
            try:
                if os.path.isfile(local_path):
                    os.remove(local_path)
            except Exception:
                pass

        session.delete(entry)
        session.commit()
        return {"deleted": True}


def _bg_synthesize_and_store(safe_id: str, headline: str):
    h = hashlib.sha256(headline.encode('utf-8')).hexdigest()[:8]
    key = f"tts/news_{safe_id}_{h}.wav"
    audio_bytes, mime = synthesize_text(headline)
    bucket = os.getenv('S3_BUCKET_NAME') or os.getenv('AWS_S3_BUCKET')
    if bucket and upload_tts_to_s3(key, audio_bytes, content_type='audio/wav'):
        with Session(engine) as session:
            entry = TTSCache(
                news_id=safe_id,
                headline_hash=h,
                storage='s3',
                key_or_path=key,
                size_bytes=len(audio_bytes),
                last_accessed_at=datetime.utcnow(),
            )
            session.add(entry)
            session.commit()
    else:
        tts_dir = os.path.join(os.path.abspath(MEDIA_DIR), "tts")
        os.makedirs(tts_dir, exist_ok=True)
        filename = f"news_{safe_id}_{h}.wav"
        filepath = os.path.join(tts_dir, filename)
        try:
            with open(filepath, 'wb') as f:
                f.write(audio_bytes)
            with Session(engine) as session:
                entry = TTSCache(
                    news_id=safe_id,
                    headline_hash=h,
                    storage='local',
                    key_or_path=f"/media/tts/{filename}",
                    url=f"/media/tts/{filename}",
                    size_bytes=len(audio_bytes),
                    last_accessed_at=datetime.utcnow(),
                )
                session.add(entry)
                session.commit()
        except Exception:
            pass
    _clear_pending(safe_id, h)


@app.post("/api/iot/news/{news_id}/tts/request")
def news_tts_request(news_id: str, background_tasks: BackgroundTasks, current_device: IoTDevice = Depends(get_current_device)):
    items = news_get_trending(limit=50)
    found = next((it for it in items if str(it.get("news_id")) == str(news_id)), None)
    if not found:
        raise HTTPException(status_code=404, detail="news item not found")
    safe_id = str(news_id).replace('/', '_')
    headline = (found.get("headline") or "").strip()
    h = hashlib.sha256(headline.encode('utf-8')).hexdigest()[:8]
    # already ready?
    with Session(engine) as session:
        existing = session.exec(select(TTSCache).where(TTSCache.news_id == safe_id, TTSCache.headline_hash == h)).first()
        if existing:
            # ready
            if existing.storage == 's3':
                url = generate_presigned_s3_url(existing.key_or_path, expires=int(os.getenv('TTS_PRESIGNED_EXPIRY', '3600')))
                return {"status": "ready", "url": url}
            return {"status": "ready", "url": existing.url}
    # schedule if not already
    if _mark_pending(safe_id, h):
        background_tasks.add_task(_bg_synthesize_and_store, safe_id, headline)
    return Response(content='{"status":"processing"}', media_type='application/json', status_code=202)


@app.get("/api/iot/news/{news_id}/tts/status")
def news_tts_status(news_id: str, current_device: IoTDevice = Depends(get_current_device)):
    items = news_get_trending(limit=50)
    found = next((it for it in items if str(it.get("news_id")) == str(news_id)), None)
    if not found:
        raise HTTPException(status_code=404, detail="news item not found")
    safe_id = str(news_id).replace('/', '_')
    headline = (found.get("headline") or "").strip()
    h = hashlib.sha256(headline.encode('utf-8')).hexdigest()[:8]
    with Session(engine) as session:
        existing = session.exec(select(TTSCache).where(TTSCache.news_id == safe_id, TTSCache.headline_hash == h)).first()
        if existing:
            if existing.storage == 's3':
                url = generate_presigned_s3_url(existing.key_or_path, expires=int(os.getenv('TTS_PRESIGNED_EXPIRY', '3600')))
                return {"status": "ready", "url": url}
            return {"status": "ready", "url": existing.url}
    if _is_pending(safe_id, h):
        return {"status": "processing"}
    return {"status": "not-started"}


# --- Interaction logging / analytics --------------------------------------------------
@app.post("/api/iot/log/interaction")
def log_interaction(payload: InteractionLogRequest, current_device: IoTDevice = Depends(get_current_device)):
    with Session(engine) as session:
        log = InteractionLog(
            device_id=current_device.device_id,
            user_id=payload.user_id,
            action_type=payload.action_type,
            query=payload.query,
            results_count=payload.results_count,
            response_time_ms=payload.response_time_ms,
        )
        session.add(log)
        session.commit()
        return {"ok": True, "log_id": log.log_id}


# --- Voice endpoints (mock implementations with provider hooks) -----------------------
@app.post("/api/iot/voice/transcribe", response_model=VoiceTranscribeResponse)
async def voice_transcribe(request: Request, current_device: IoTDevice = Depends(get_current_device), _rl: None = Depends(get_rate_limiter(limit=60, window_s=60))):
    """Accept audio as raw body (application/octet-stream) or JSON {"audio_base64": "..."} and return transcribed text.

    Uses provider-agnostic `app.voice` module which falls back to a deterministic mock when no provider is configured.
    """
    ct = request.headers.get("content-type", "")
    try:
        if "application/json" in ct:
            body = await request.json()
            b64 = body.get("audio_base64")
            if not b64:
                raise HTTPException(status_code=400, detail="audio_base64 is required in JSON")
            data = base64.b64decode(b64)
        else:
            data = await request.body()
    except Exception:
        raise HTTPException(status_code=400, detail="could not read audio payload")

    text = transcribe_from_bytes(data)
    return VoiceTranscribeResponse(text=text)


def _generate_silence_wav(duration_s: float = 0.12, rate: int = 8000) -> bytes:
    # 16-bit PCM mono silence WAV
    n_samples = int(duration_s * rate)
    byte_rate = rate * 2
    block_align = 2
    data_size = n_samples * 2
    # RIFF header
    header = b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE"
    # fmt subchunk
    fmt = b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, byte_rate, block_align, 16)
    # data subchunk
    data = b"data" + struct.pack("<I", data_size) + (b"\x00\x00" * n_samples)
    return header + fmt + data


@app.post("/api/iot/voice/tts", response_model=TTSResponse)
def voice_tts(payload: dict, current_device: IoTDevice = Depends(get_current_device), _rl: None = Depends(get_rate_limiter(limit=60, window_s=60))):
    text = payload.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    audio_bytes, mime = synthesize_text(text)
    b64 = base64.b64encode(audio_bytes).decode("ascii")
    return TTSResponse(audio_base64=b64, mime_type=mime)


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


@app.get("/api/iot/preferences/{user_id}")
def get_preferences(user_id: int, current_device: IoTDevice = Depends(get_current_device)):
    """Get user preferences for language, region, categories."""
    with Session(engine) as session:
        statement = select(UserPreference).where(
            UserPreference.device_id == current_device.device_id,
            UserPreference.user_id == user_id
        )
        pref = session.exec(statement).first()
        if not pref:
            # return defaults
            return {"language": "en", "region": "in", "categories": None}
        return {
            "language": pref.language,
            "region": pref.region,
            "categories": pref.categories,
            "updated_at": pref.updated_at.isoformat() if pref.updated_at else None
        }


@app.post("/api/iot/preferences/{user_id}")
def set_preferences(user_id: int, payload: dict, current_device: IoTDevice = Depends(get_current_device)):
    """Set/update user preferences for language, region, categories."""
    with Session(engine) as session:
        statement = select(UserPreference).where(
            UserPreference.device_id == current_device.device_id,
            UserPreference.user_id == user_id
        )
        pref = session.exec(statement).first()
        if not pref:
            # create new
            pref = UserPreference(
                device_id=current_device.device_id,
                user_id=user_id,
                language=payload.get("language", "en"),
                region=payload.get("region", "in"),
                categories=payload.get("categories")
            )
            session.add(pref)
        else:
            # update existing
            if "language" in payload:
                pref.language = payload["language"]
            if "region" in payload:
                pref.region = payload["region"]
            if "categories" in payload:
                pref.categories = payload["categories"]
            pref.updated_at = datetime.utcnow()
            session.add(pref)
        session.commit()
        session.refresh(pref)
        return {
            "language": pref.language,
            "region": pref.region,
            "categories": pref.categories,
            "updated_at": pref.updated_at.isoformat() if pref.updated_at else None
        }


@app.get("/api/iot/analytics/summary")
def analytics_summary(current_device: IoTDevice = Depends(get_current_device)):
    """Return aggregated analytics summary for the current device."""
    with Session(engine) as session:
        # Total interactions
        total = session.exec(select(InteractionLog).where(InteractionLog.device_id == current_device.device_id)).all()
        total_count = len(total)
        
        # Group by action_type
        action_counts = {}
        for log in total:
            action = log.action_type or "unknown"
            action_counts[action] = action_counts.get(action, 0) + 1
        
        # Recent 10 interactions
        recent = session.exec(
            select(InteractionLog)
            .where(InteractionLog.device_id == current_device.device_id)
            .order_by(InteractionLog.timestamp.desc())
            .limit(10)
        ).all()
        
        recent_list = [
            {
                "log_id": r.log_id,
                "action_type": r.action_type,
                "query": r.query,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None
            }
            for r in recent
        ]
        
        return {
            "total_interactions": total_count,
            "by_action": action_counts,
            "recent": recent_list
        }


@app.get("/api/iot/analytics/interactions")
def analytics_interactions(limit: int = 50, offset: int = 0, current_device: IoTDevice = Depends(get_current_device)):
    """Return paginated interaction logs for the current device."""
    with Session(engine) as session:
        logs = session.exec(
            select(InteractionLog)
            .where(InteractionLog.device_id == current_device.device_id)
            .order_by(InteractionLog.timestamp.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        
        return {
            "data": [
                {
                    "log_id": log.log_id,
                    "user_id": log.user_id,
                    "action_type": log.action_type,
                    "query": log.query,
                    "results_count": log.results_count,
                    "response_time_ms": log.response_time_ms,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None
                }
                for log in logs
            ],
            "limit": limit,
            "offset": offset
        }

