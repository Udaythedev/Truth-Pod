# Firmware API Compatibility Update

## Overview
Updated ESP32 firmware to match the actual backend API response formats after free-tier migration.

## Changes Made

### ESP32 Main Board (`esp32_main.ino`)

#### 1. News Response Parsing
**Issue:** Backend returns `{"data": [...]}` but firmware expected `{"articles": [...]}`

**Fixed:**
- Changed `doc["articles"]` to `doc["data"]`
- Changed `article["id"]` to `article["news_id"]`
- Changed `article["title"]` to `article["headline"]`
- Removed parsing of `description` and `publishedAt` (not in minimal response)

**Backend Response Format:**
```json
{
  "data": [
    {
      "news_id": "abc123",
      "headline": "Breaking news headline",
      "source": "News Source",
      "confidence": 0.95,
      "url": "https://..."
    }
  ]
}
```

#### 2. TTS Audio Response
**Issue:** Backend returns `audio_base64` but firmware expected `audio_data`

**Fixed:**
- Changed `doc["audio_data"]` to `doc["audio_base64"]`
- Added parsing of `mime_type` field (gTTS returns `audio/mpeg`)

**Backend Response Format:**
```json
{
  "audio_base64": "UklGRi4uLg==...",
  "mime_type": "audio/mpeg"
}
```

#### 3. Trending News Endpoint
**Issue:** Firmware used wrong endpoint path and unsupported parameters

**Fixed:**
- Changed `/api/iot/news/trending?region=in&category=general` to `/api/iot/trending?region=in&limit=5`
- Backend only supports `region` and `limit` parameters (no `category`)

#### 4. Search News Endpoint
**Issue:** Firmware used wrong query parameter name

**Fixed:**
- Changed `/api/iot/news/search?q=...` to `/api/iot/search?query=...`
- Backend expects `query` parameter, not `q`

### ESP32-CAM Board (`esp32_cam.ino`)

#### 1. Face Recognition Request
**Issue:** Backend expects `image_base64` but firmware sent `image_data`

**Fixed:**
- Changed payload field from `image_data` to `image_base64`
- Updated response parsing to check `user_name != "UNKNOWN"` instead of `matched` boolean

**Backend Request Format:**
```json
{
  "image_base64": "iVBORw0KGgo..."
}
```

**Backend Response Format:**
```json
{
  "user_id": 123,
  "user_name": "John Doe",
  "confidence": 0.95
}
```
Or when no match:
```json
{
  "user_id": null,
  "user_name": "UNKNOWN",
  "confidence": 0.45
}
```

#### 2. Face Enrollment Request
**Issue:** Backend expects `image_base64` but firmware sent `image_data`

**Fixed:**
- Changed payload field from `image_data` to `image_base64`
- Updated response parsing to match actual backend fields

**Backend Request Format:**
```json
{
  "user_name": "John Doe",
  "image_base64": "iVBORw0KGgo..."
}
```

**Backend Response Format:**
```json
{
  "user_id": 123,
  "user_name": "John Doe",
  "face_image_url": "/media/face_device123_user456.jpg"
}
```

## Testing Checklist

### Main Board
- [ ] Device registration works and stores JWT token
- [ ] Trending news fetches correctly (3-5 articles)
- [ ] Search news works with voice transcription
- [ ] News articles display with proper title/source/confidence
- [ ] TTS audio plays (MP3 format from gTTS)
- [ ] Audio streaming works from B2/S3 URLs

### ESP32-CAM
- [ ] Face enrollment creates new user
- [ ] Face recognition returns correct user_id
- [ ] "NO_FACE" sent when no match found
- [ ] UART communication with main board works
- [ ] LED indicators blink correctly

## Backend Endpoints Reference

All endpoints require `Authorization: Bearer <jwt_token>` header.

### News
- `GET /api/iot/trending?region=in&limit=5` → `{"data": [NewsItem]}`
- `GET /api/iot/search?query=<text>&limit=10` → `{"data": [NewsItem]}`

### TTS
- `GET /api/iot/news/{news_id}/tts` → `{"audio_base64": "...", "mime_type": "audio/mpeg"}`
- `GET /api/iot/news/{news_id}/tts/url` → `{"url": "https://...", "expires_in": 3600}`

### Voice
- `POST /api/iot/voice/transcribe` with `{"audio_base64": "..."}` → `{"text": "..."}`
- `POST /api/iot/voice/tts` with `{"text": "..."}` → `{"audio_base64": "...", "mime_type": "audio/mpeg"}`

### Face
- `POST /api/iot/face/enroll` with `{"user_name": "...", "image_base64": "..."}` → `{"user_id": 123, ...}`
- `POST /api/iot/face/recognize` with `{"image_base64": "..."}` → `{"user_id": 123 or null, "user_name": "...", "confidence": 0.95}`

## Important Notes

1. **Audio Format**: Backend now returns MP3 (from gTTS) instead of WAV. Ensure your I2S audio library supports MP3 decoding.

2. **TTS Streaming**: Consider using `/api/iot/news/{id}/tts/url` endpoint to get a presigned B2/S3 URL and stream audio directly instead of loading full base64 into memory.

3. **Region Parameter**: Backend supports different regions for news (e.g., "in", "us", "gb"). Update firmware to make this configurable.

4. **Error Handling**: All endpoints may return 401 if token expires. Implement token rotation via `/api/iot/device/token/rotate`.

5. **Rate Limits**: Default limits are 120 requests/minute per device. Voice endpoints have 60 requests/minute.

## Deployment Steps

1. Update firmware files with these changes
2. Update `API_BASE_URL` in both `.ino` files to your Render backend URL
3. Update WiFi credentials
4. Flash firmware to ESP32 boards
5. Test device registration and token storage
6. Test news fetching and TTS playback
7. Test face enrollment and recognition

## Free-Tier Considerations

- **gTTS**: Returns MP3 format, slightly slower than Google Cloud TTS but unlimited and free
- **Deepgram STT**: 200 minutes/month free; falls back to mock if key not set
- **B2 Storage**: TTS audio cached in Backblaze B2 (10GB free)
- **Render**: Free tier includes 750 hours/month

All free-tier services are production-ready for hackathons and student projects!
