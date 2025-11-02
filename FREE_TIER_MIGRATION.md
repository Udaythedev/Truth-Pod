# 🎉 TruthPod - Free Tier Migration Complete!

## What Changed

Your TruthPod backend now runs **100% free** using student-friendly cloud services instead of paid Google Cloud and AWS.

### Before (Paid Services)
- ❌ Google Cloud Speech-to-Text (~$0.006/15sec)
- ❌ Google Cloud Text-to-Speech (~$4/1M chars)
- ❌ AWS S3 (requires payment setup)
- ❌ **Total: $20-50+/month for moderate usage**

### After (Free Services)
- ✅ **Deepgram STT**: 200 minutes/month FREE
- ✅ **gTTS (Google Translate TTS)**: Unlimited FREE, no API key!
- ✅ **Local/Cloudflare R2 storage**: 10GB FREE
- ✅ **Total: $0/month** 🎉

---

## Files Modified

### New Files Created
1. **`backend/app/voice_free.py`** - Free-tier STT/TTS implementation
2. **`backend/app/storage.py`** - Storage abstraction (local/R2/S3)
3. **`FREE_TIER_SETUP.md`** - Complete setup guide for students
4. **`FREE_TIER_MIGRATION.md`** - This file

### Updated Files
1. **`backend/requirements.txt`**
   - Added: `gTTS>=2.4.0` (free unlimited TTS)
   - Added: `deepgram-sdk>=3.0.0` (free 200 min/month STT)
   - Kept: `boto3` (for optional R2/S3 storage)

2. **`backend/.env`**
   - Added: `USE_FREE_VOICE=1` (enables free services)
   - Added: `DEEPGRAM_API_KEY=your_key_here` (get at console.deepgram.com)
   - Added: `STORAGE_BACKEND=local` (or `r2` for Cloudflare R2)
   - Replaced Google Cloud vars with optional comments

3. **`backend/.env.example`**
   - Updated with free-tier options and upgrade paths

4. **`backend/app/main.py`**
   - Added conditional import: uses `voice_free.py` when `USE_FREE_VOICE=1`
   - Backward compatible: still supports Google Cloud if configured

5. **`backend/README.md`**
   - Added free-tier overview and link to setup guide

---

## How to Use

### Quick Start (Free Tier)

1. **Get Deepgram API Key** (200 min/month free):
   ```
   https://console.deepgram.com/signup
   ```
   Add to `backend/.env`:
   ```bash
   USE_FREE_VOICE=1
   DEEPGRAM_API_KEY=your_deepgram_api_key_here
   ```

2. **Install new dependencies** (already done!):
   ```powershell
   cd backend
   .\.venv\Scripts\pip install gTTS deepgram-sdk
   ```

3. **Run backend**:
   ```powershell
   cd backend
   .\.venv\Scripts\uvicorn app.main:app --reload
   ```

That's it! gTTS works without any API key.

### Optional: Cloudflare R2 Storage (10GB free)

For persistent audio storage across deployments:

1. Create R2 bucket at https://dash.cloudflare.com/
2. Get API credentials
3. Update `backend/.env`:
   ```bash
   STORAGE_BACKEND=r2
   R2_ACCOUNT_ID=your_account_id
   R2_ACCESS_KEY_ID=your_access_key
   R2_SECRET_ACCESS_KEY=your_secret_key
   R2_BUCKET_NAME=truthpod-audio
   ```

---

## Testing

### Test STT (Speech-to-Text)
```powershell
# Will use Deepgram if API key is set, otherwise falls back to mock
curl -X POST http://localhost:8000/api/iot/voice/transcribe \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "audio=@test.wav"
```

### Test TTS (Text-to-Speech)
```powershell
# Uses gTTS (free, unlimited)
curl http://localhost:8000/api/iot/news/123/tts \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Cost Breakdown

| Service | Free Tier Limit | After Limit | Notes |
|---------|----------------|-------------|-------|
| **Deepgram STT** | 200 min/month | $0.0043/min | Very affordable upgrade |
| **gTTS** | ♾️ Unlimited | Always free | Google Translate TTS |
| **Cloudflare R2** | 10GB storage | $0.015/GB/mo | No egress fees! |
| **NewsAPI** | 100 req/day | $449/mo | Enough for dev/testing |
| **Gemini API** | Rate-limited | Pay-as-you-go | Free tier very generous |
| **Upstash Redis** | 10K cmd/day | $0.2/100K | Optional caching |

**Your monthly cost: $0** for development and low-traffic production!

---

## Upgrade Path (When Funded)

When your project gets funding or significant users:

### Phase 1: Light Traffic (~100-500 users)
- Keep free tier
- Add Cloudflare R2 for persistent storage
- **Cost: $0-5/month**

### Phase 2: Growing (~1K-10K users)
- Upgrade Deepgram to paid ($0.0043/min - very cheap!)
- Add Render standard tier ($7/mo for always-on)
- Consider ElevenLabs for better TTS quality
- **Cost: ~$30-50/month**

### Phase 3: Scale (10K+ users)
- Switch to Google Cloud TTS for custom voices
- Add AWS S3 + CloudFront CDN
- Upgrade to Vertex AI for better verification
- **Cost: $100-300/month**

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│ ESP32 IoT Device (Your Hardware)                    │
│  - Microphone → captures audio                      │
│  - Speaker → plays TTS audio                        │
│  - Camera → face recognition                        │
└─────────────────┬───────────────────────────────────┘
                  │ HTTPS REST API
┌─────────────────▼───────────────────────────────────┐
│ FastAPI Backend (Cloud-hosted, free tier)           │
│  ┌──────────────────────────────────────────────┐  │
│  │ Voice Services (FREE!)                        │  │
│  │  - STT: Deepgram (200 min/month)            │  │
│  │  - TTS: gTTS (unlimited!)                    │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │ Storage (FREE!)                               │  │
│  │  - Local files OR Cloudflare R2 (10GB)      │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │ News & AI (FREE TIER!)                       │  │
│  │  - NewsAPI (100 req/day)                     │  │
│  │  - Gemini API (rate-limited)                 │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## What's Next?

1. **Get Deepgram API key**: https://console.deepgram.com/signup
2. **Test locally**: Run backend with `USE_FREE_VOICE=1`
3. **Deploy free**: Use Render/Railway/Fly.io free tier
4. **Add monitoring**: Optional Sentry free tier (5K events/month)
5. **Scale when ready**: Smooth upgrade path documented above

---

## Documentation

- **Full setup guide**: [FREE_TIER_SETUP.md](./FREE_TIER_SETUP.md)
- **API keys guide**: [backend/API_KEYS.md](./backend/API_KEYS.md)
- **Backend README**: [backend/README.md](./backend/README.md)
- **Firmware guides**: [firmware/README.md](./firmware/README.md)

---

## Support & Resources

- **Deepgram Docs**: https://developers.deepgram.com/
- **gTTS Docs**: https://gtts.readthedocs.io/
- **Cloudflare R2**: https://developers.cloudflare.com/r2/
- **Render Free Tier**: https://render.com/docs/free

---

## Summary

✅ **Migrated to 100% free cloud services**  
✅ **Zero breaking changes** (backward compatible)  
✅ **Production-ready** for student projects  
✅ **Clear upgrade path** when you get funding  

**Your TruthPod is now cost-free and ready to scale! 🚀**
