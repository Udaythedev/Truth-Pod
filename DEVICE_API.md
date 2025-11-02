# TruthPod Device API — Quick Reference

This document shows the device-facing API endpoints, example payloads (curl / PowerShell), and practical notes for ESP32 firmware developers.

Base URL
- For local development (backend running on localhost/port): http://<host>:8000
- In production use the configured HTTPS endpoint (TLS required).

Authentication
- After registration the backend returns an `api_token` (JWT). Include this header on protected endpoints:

  Authorization: Bearer <api_token>

Common headers
- Content-Type: application/json
- Accept: application/json

1) Device registration

POST /api/iot/device/register

Request (JSON):

{
  "device_mac": "AA:BB:CC:11:22:33",
  "device_name": "TruthPod-001",
  "device_type": "ESP32"
}

Response (201):

{
  "device_id": "<uuid>",
  "api_token": "<jwt-token>"
}

PowerShell example:

```powershell
$body = @{ device_mac = 'AA:BB:CC:11:22:33'; device_name = 'TruthPod-001'; device_type = 'ESP32' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/api/iot/device/register' -ContentType 'application/json' -Body $body
```

2) Trending

GET /api/iot/trending?region=in&limit=5

Headers: Authorization: Bearer <api_token>

Response: { "data": [ { news_id, headline, source, confidence, url }, ... ] }

3) Search

GET /api/iot/search?query=battery&limit=5

Headers: Authorization: Bearer <api_token>

4) Face enroll

POST /api/iot/face/enroll

Request (JSON):

{
  "user_name": "Alice",
  "image_base64": "<base64 jpeg bytes>"
}

Response: { "user_id": 1, "user_name": "Alice", "face_image_url": "/media/face_..." }

Notes: Keep images small (e.g., 320×240 or 480×360 JPEG). Compress/rescale on-device before base64 encoding. Limit payloads to a few hundred KB.

5) Face recognize

POST /api/iot/face/recognize

Request (JSON): { "image_base64": "<base64 jpeg bytes>" }

Response: { "user_id": <int>|null, "user_name": "Alice"|"UNKNOWN", "confidence": 0.### }

6) Heartbeat

POST /api/iot/device/heartbeat

Request (JSON): { "firmware_version": "0.1.2" }

Response: { "ok": true, "device_id": "..." }

7) Device status / OTA

GET /api/iot/device/status

Response: device metadata including `ota_update_available` and `ota_firmware_url`.

8) Interaction logging

POST /api/iot/log/interaction

Request (JSON):

{
  "action_type": "search",
  "query": "battery" ,
  "user_id": 1,
  "results_count": 3,
  "response_time_ms": 123
}

9) Voice (mock STT/TTS) — for testing

POST /api/iot/voice/transcribe
- Accepts raw bytes (application/octet-stream) or JSON { "audio_base64": "..." }
- Returns deterministic mock transcription (useful for device flow tests).

POST /api/iot/voice/tts
- Request: { "text": "Hello world" }
- Returns: tiny placeholder WAV as base64 (replace with real TTS provider in production).

Practical tips for embedded developers
- Use the Authorization header with Bearer token for all protected endpoints.
- Compress images before base64 encoding. Prefer JPEG and target <200KB per image for good bandwidth.
- Implement retry/backoff for network calls; store the token in non-volatile storage (NVS) or SPIFFS securely.
- Cache last trending/search results locally for offline operation.

If you'd like, I can add a small Arduino (ESP32) sketch showing registration, storing the token in Preferences, and calling trending and face endpoints.
