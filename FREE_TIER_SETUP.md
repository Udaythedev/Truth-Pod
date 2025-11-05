# 🎓 Free Tier Setup Guide for Students

This guide helps you run TruthPod completely free using student-friendly cloud services. Perfect for prototypes, hackathons, and bootstrapped startups.

## 🎯 Zero-Cost Stack

| Service | Provider | Free Tier | What You Get |
|---------|----------|-----------|--------------|
| Backend Hosting | Render / Railway / Fly.io | Free | 750 hrs/month (Render), always-on free tier |
| Database | Supabase / Render | Free | 500MB Postgres (Supabase), 90-day SQLite (Render) |
| Redis Cache | Upstash | Free | 10K commands/day |
| News API | NewsAPI.org | Free | 100 requests/day for dev |
| Speech-to-Text | Deepgram | Free | 200 min/month |
| Text-to-Speech | gTTS | Free | Unlimited (no API key) |
| AI Verification | Gemini API | Free | Rate-limited, suitable for dev |
| Audio Storage | Local / Cloudflare R2 | Free | 10GB + no egress fees (R2) |
| Git Hosting | GitHub | Free | Unlimited repos + Actions |

Total monthly cost: $0

---

## 📝 Step-by-Step Setup

### 1. News API (Required)
Get a free API key:
- Provider: https://newsapi.org
- Free tier: 100 requests/day
- Sign up and create a key

Add to .env:
```bash
NEWSAPI_KEY=your_newsapi_key_here
```

---

### 2. Speech-to-Text: Deepgram (Free 200 min/month)

Get your free API key:
1. https://console.deepgram.com/signup
2. Sign up with GitHub (student email can get extra credits)
3. Create a new project
4. Copy your API key

Add to .env:
```bash
USE_FREE_VOICE=1
DEEPGRAM_API_KEY=your_deepgram_api_key_here
```

Limits:
- 200 minutes/month free
- Nova-2 model (great quality)
- 50+ languages
- Very affordable beyond free tier

---

### 3. Text-to-Speech: gTTS (Unlimited Free)

No API key needed. gTTS uses Google Translate’s TTS engine.

Already configured:
```bash
USE_FREE_VOICE=1
```

Notes:
- Completely free, unlimited usage
- 50+ languages, MP3 output
- Requires internet connection

---

### 4. AI Verification: Gemini API (Free)

Get your free API key:
1. https://aistudio.google.com/app/apikey
2. Sign in → Create API Key → Copy

Add to .env:
```bash
GEMINI_API_KEY=***REMOVED***
```

Important: Keep your key secret. Never commit it to Git.

---

### 5. Audio Storage: Choose Your Path

Option A: Local Storage (simplest)
```bash
STORAGE_BACKEND=local
MEDIA_DIR=./media
```
Pros: Zero setup, immediate.  Cons: Files reset if server restarts (Render free tier).

Option B: Cloudflare R2 (recommended for production)
Setup:
1. https://dash.cloudflare.com/ → R2 → Create bucket (truthpod-audio)
2. Create API token → Copy Account ID, Access Key ID, Secret Access Key

Add to .env:
```bash
STORAGE_BACKEND=r2
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET_NAME=truthpod-audio
```

---

### 6. Redis Cache: Upstash (Free 10K commands/day)

Get a free Redis URL:
1. https://console.upstash.com/ → Create database (free)
2. Copy the Redis URL

Add to .env:
```bash
REDIS_URL=redis://default:your_password@your-endpoint.upstash.io:6379
```

Alternative (local Redis on Windows):
```powershell
choco install redis-64
redis-server
# then
REDIS_URL=redis://localhost:6379/0
```

---

### 7. Database

Production (Render PostgreSQL):
1. https://dashboard.render.com/ → New → PostgreSQL (Free)
2. Copy the Internal Database URL

Add to .env:
```bash
DATABASE_URL=postgresql://user:pass@host/db
```

Local development (SQLite):
```bash
DATABASE_URL=sqlite:///./truthpod.db
```

---

## 🚀 Install Dependencies

```powershell
cd backend
pip install -r requirements.txt
```

Added packages for free tier:
- gTTS (TTS)
- deepgram-sdk (STT)

---

## ✅ Verify Your Setup

```powershell
$env:USE_FREE_VOICE="1"
python -m pytest backend/tests/ -v

# Start backend (local)
cd backend
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for interactive API.

---

## 📊 Usage Tracking & Limits

| Service | Monthly Limit | Monitor |
|---------|---------------|---------|
| NewsAPI | 100 req/day | https://newsapi.org/account |
| Deepgram STT | 200 minutes | https://console.deepgram.com/ |
| gTTS | Unlimited | N/A |
| Gemini API | Rate-limited | Errors show in logs |
| Upstash Redis | 10K commands/day | https://console.upstash.com/ |
| Cloudflare R2 | 10GB | https://dash.cloudflare.com/ |

---

## 💡 Cost Optimization Tips

1. Cache news (5m), TTS audio (persistent), verification results (24h)
2. Generate TTS lazily (on-request)
3. Prefer MP3 (gTTS) for small payloads
4. Batch network operations
5. Add provider dashboard alerts

---

## 🎓 Upgrade Path (When You Get Funding)

| Current (Free) | Upgrade To | Cost | Why |
|----------------|------------|------|-----|
| Deepgram free | Deepgram paid | ~$0.0043/min | More minutes, lower latency |
| gTTS | ElevenLabs / Google Cloud TTS | $15–30/1M chars | Higher quality, custom voices |
| Local/R2 | AWS S3 + CloudFront | ~$5–20/mo | Global CDN, faster delivery |
| Render free | Render Standard | $7/mo | No sleep, more resources |
| Gemini free | Vertex AI | ~$0.50/1K reqs | SLA, higher limits |

---

## 🆘 Troubleshooting

gTTS not installed
```powershell
pip install gTTS
```

Deepgram key invalid
- Ensure DEEPGRAM_API_KEY=your_key_here in .env
- Check console: https://console.deepgram.com/

Audio file not found (local)
- Ensure backend/media exists
- On Render, prefer R2 (files persist across restarts)

Redis connection failed
- Local: start Redis server
- Cloud: verify Upstash URL & credentials

---

## 📚 Additional Resources

- Deepgram Docs: https://developers.deepgram.com/docs
- gTTS Docs: https://gtts.readthedocs.io/
- Cloudflare R2: https://developers.cloudflare.com/r2/
- Upstash Redis: https://docs.upstash.com/redis
- Render: https://render.com/docs

---

## 🎉 You're All Set

TruthPod now runs 100% free with real STT, unlimited TTS, persistent/cloud storage, caching, and verification. Perfect for student projects, hackathons, and early-stage builds. Scale when you’re ready.

