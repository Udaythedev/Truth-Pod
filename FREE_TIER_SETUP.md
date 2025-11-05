# 🎓 Free Tier Setup Guide for Students# 🎓 Free Tier Setup Guide for Students



This guide helps you run **TruthPod completely free** using student-friendly cloud services. Perfect for prototypes, hackathons, and bootstrapped startups!This guide helps you run **TruthPod completely free** using student-friendly cloud services. Perfect for prototypes, hackathons, and bootstrapped startups!



## 🎯 Zero-Cost Stack## 🎯 Zero-Cost Stack



| Service | Provider | Free Tier | What You Get || Service | Provider | Free Tier | What You Get |

|---------|----------|-----------|--------------||---------|----------|-----------|--------------|

| **Backend Hosting** | Render / Railway / Fly.io | ✅ Free | 750 hrs/month (Render), always-on free tier || **Backend Hosting** | Render / Railway / Fly.io | ✅ Free | 750 hrs/month (Render), always-on free tier |

| **Database** | Supabase / Render | ✅ Free | 500MB Postgres (Supabase), 90-day SQLite (Render) || **Database** | Supabase / Render | ✅ Free | 500MB Postgres (Supabase), 90-day SQLite (Render) |

| **Redis Cache** | Upstash | ✅ Free | 10K commands/day || **Redis Cache** | Upstash | ✅ Free | 10K commands/day |

| **News API** | NewsAPI.org | ✅ Free | 100 requests/day for dev || **News API** | NewsAPI.org | ✅ Free | 100 requests/day for dev |

| **Speech-to-Text** | Deepgram | ✅ Free | 200 min/month || **Speech-to-Text** | Deepgram | ✅ Free | 200 min/month |

| **Text-to-Speech** | gTTS | ✅ Free | Unlimited (no API key!) || **Text-to-Speech** | gTTS | ✅ Free | Unlimited (no API key!) |

| **AI Verification** | Gemini API | ✅ Free | Rate-limited, perfect for dev || **AI Verification** | Gemini API | ✅ Free | Rate-limited, perfect for dev |

| **Audio Storage** | Local / Cloudflare R2 | ✅ Free | 10GB + no egress fees (R2) || **Audio Storage** | Local / Cloudflare R2 | ✅ Free | 10GB + no egress fees (R2) |

| **Git Hosting** | GitHub | ✅ Free | Unlimited repos + Actions || **Git Hosting** | GitHub | ✅ Free | Unlimited repos + Actions |



**Total monthly cost: $0** 🎉**Total monthly cost: $0** 🎉



------



## 📝 Step-by-Step Setup## 📝 Step-by-Step Setup



### 1. News API (Required)### 1. News API (Required)

**Get your free API key:****Get your free API key:**

- Provider: https://newsapi.org- Provider: https://newsapi.org

- Free tier: 100 requests/day- Free tier: 100 requests/day

- Sign up and get your key- Sign up and get your key



**Add to `.env`:****Add to `.env`:**

```bash```bash

NEWSAPI_KEY=your_newsapi_key_hereNEWSAPI_KEY=your_newsapi_key_here

``````



------



### 2. Speech-to-Text: Deepgram (Free 200 min/month)### 2. Speech-to-Text: Deepgram (Free 200 min/month)



**Get your free API key:****Get your free API key:**

1. Go to https://console.deepgram.com/signup1. Go to https://console.deepgram.com/signup

2. Sign up with GitHub (student email for extra credits if available)2. Sign up with GitHub (student email for extra credits if available)

3. Create a new project3. Create a new project

4. Copy your API key from the dashboard4. Copy your API key from the dashboard



**Add to `.env`:****Add to `.env`:**

```bash```bash

USE_FREE_VOICE=1USE_FREE_VOICE=1

DEEPGRAM_API_KEY=your_deepgram_api_key_hereDEEPGRAM_API_KEY=your_deepgram_api_key_here

``````



**Limits:****Limits:**

- ✅ 200 minutes/month free- ✅ 200 minutes/month free

- ✅ Nova-2 model (best quality)- ✅ Nova-2 model (best quality)

- ✅ 50+ languages- ✅ 50+ languages

- Upgrades: $0.0043/min after free tier (very affordable)- Upgrades: $0.0043/min after free tier (very affordable)



------



### 3. Text-to-Speech: gTTS (Unlimited Free!)### 3. Text-to-Speech: gTTS (Unlimited Free!)



**No API key needed!** gTTS uses Google Translate's TTS engine.**No API key needed!** gTTS uses Google Translate's TTS engine.



**Already configured:****Already configured:**

```bash```bash

USE_FREE_VOICE=1  # This enables gTTS automaticallyUSE_FREE_VOICE=1  # This enables gTTS automatically

``````



**Features:****Features:**

- ✅ Completely free, unlimited usage- ✅ Completely free, unlimited usage

- ✅ 50+ languages- ✅ 50+ languages

- ✅ Good quality (MP3 output)- ✅ Good quality (MP3 output)

- ✅ No registration required- ✅ No registration required

- ⚠️ Requires internet connection (calls Google Translate)- ⚠️ Requires internet connection (calls Google Translate)



------



### 4. AI Verification: Gemini API (Free Rate-Limited)### 4. AI Verification: Gemini API (Free Rate-Limited)



**Get your free API key:****Get your free API key:**

1. Go to https://aistudio.google.com/app/apikey1. Go to https://aistudio.google.com/app/apikey

2. Sign in with Google account2. Sign in with Google account

3. Click "Create API Key"3. Click "Create API Key"

4. Copy your key4. Copy your key



**Add to `.env`:****Add to `.env`:**

```bash```bash

GEMINI_API_KEY=***REMOVED***=your_gemini_api_key_here

``````



**Important:** Keep your API key secure and never commit it to Git!**Important:** Keep your API key secure and never commit it to Git!



------



### 5. Audio Storage: Choose Your Path### 5. Audio Storage: Choose Your Path



#### Option A: Local Storage (Simplest)#### Option A: Local Storage (Simplest)

**Already configured!** Audio files saved to `backend/media/`**Already configured!** Audio files saved to `backend/media/`



```bash```bash

STORAGE_BACKEND=localSTORAGE_BACKEND=local

MEDIA_DIR=./mediaMEDIA_DIR=./media

``````



**Pros:** Zero setup, works immediately  **Pros:** Zero setup, works immediately  

**Cons:** Files lost if server restarts (on Render free tier)**Cons:** Files lost if server restarts (on Render free tier)



#### Option B: Cloudflare R2 (Recommended for Production)#### Option B: Cloudflare R2 (Recommended for Production)

**Free tier: 10GB storage + no egress fees****Free tier: 10GB storage + no egress fees**



**Setup:****Setup:**

1. Go to https://dash.cloudflare.com/1. Go to https://dash.cloudflare.com/

2. Sign up (free account)2. Sign up (free account)

3. Go to R2 → Create bucket → Name it `truthpod-audio`3. Go to R2 → Create bucket → Name it `truthpod-audio`

4. Go to "Manage R2 API Tokens" → Create API token4. Go to "Manage R2 API Tokens" → Create API token

5. Copy: Account ID, Access Key ID, Secret Access Key5. Copy: Account ID, Access Key ID, Secret Access Key



**Add to `.env`:****Add to `.env`:**

```bash```bash

STORAGE_BACKEND=r2STORAGE_BACKEND=r2

R2_ACCOUNT_ID=your_account_idR2_ACCOUNT_ID=your_account_id

R2_ACCESS_KEY_ID=your_access_keyR2_ACCESS_KEY_ID=your_access_key

R2_SECRET_ACCESS_KEY=your_secret_keyR2_SECRET_ACCESS_KEY=your_secret_key

R2_BUCKET_NAME=truthpod-audioR2_BUCKET_NAME=truthpod-audio

``````



**Pros:** Persistent, CDN-backed, generous free tier  **Pros:** Persistent, CDN-backed, generous free tier  

**Cons:** 5-minute setup vs instant local storage**Cons:** 5-minute setup vs instant local storage



------



### 6. Redis Cache: Upstash (Free 10K commands/day)### 6. Redis Cache: Upstash (Free 10K commands/day)



**Get your free Redis URL:****Get your free Redis URL:**

1. Go to https://console.upstash.com/1. Go to https://console.upstash.com/

2. Sign up with GitHub2. Sign up with GitHub

3. Create database → Select free tier (10K commands/day)3. Create database → Select free tier (10K commands/day)

4. Copy the Redis URL4. Copy the Redis URL



**Add to `.env`:****Add to `.env`:**

```bash```bash

REDIS_URL=redis://default:your_password@your-endpoint.upstash.io:6379REDIS_URL=redis://default:your_password@your-endpoint.upstash.io:6379

``````



**Alternative:** Run Redis locally:**Alternative:** Run Redis locally:

```powershell```powershell

# Install via Chocolatey or WSL# Install via Chocolatey or WSL

choco install redis-64choco install redis-64

redis-serverredis-server



# Then use:# Then use:

REDIS_URL=redis://localhost:6379/0REDIS_URL=redis://localhost:6379/0

``````



------



### 7. Database: Render PostgreSQL (Free)### 7. Database: Render PostgreSQL (Free)



**For production deployment:****For production deployment:**

1. Go to https://dashboard.render.com/1. Go to https://dashboard.render.com/

2. Sign up with GitHub2. Sign up with GitHub

3. New → PostgreSQL → Free plan3. New → PostgreSQL → Free plan

4. Copy the "Internal Database URL"4. Copy the "Internal Database URL"



**Add to `.env` (production only):****Add to `.env` (production only):**

```bash```bash

DATABASE_URL=postgresql://user:pass@host/dbDATABASE_URL=postgresql://user:pass@host/db

``````



**For local dev:** Keep using SQLite (already configured):**For local dev:** Keep using SQLite (already configured):

```bash```bash

DATABASE_URL=sqlite:///./truthpod.dbDATABASE_URL=sqlite:///./truthpod.db

``````



------



## 🚀 Install Dependencies## 🚀 Install Dependencies



```powershell```powershell

cd backendcd backend

pip install -r requirements.txtpip install -r requirements.txt

``````



New free-tier packages added:New free-tier packages added:

- `gTTS` - Free unlimited TTS- `gTTS` - Free unlimited TTS

- `deepgram-sdk` - Free 200 min/month STT- `deepgram-sdk` - Free 200 min/month STT



------



## ✅ Verify Your Setup## ✅ Verify Your Setup



```powershell```powershell

# Check free voice services are enabled# Check free voice services are enabled

$env:USE_FREE_VOICE="1"$env:USE_FREE_VOICE="1"

python -m pytest backend/tests/ -vpython -m pytest backend/tests/ -v



# Start backend# Start backend

cd backendcd backend

uvicorn app.main:app --reloaduvicorn app.main:app --reload

``````



Visit http://localhost:8000/docs to test endpoints!Visit http://localhost:8000/docs to test endpoints!



------



## 📊 Usage Tracking & Limits## 📊 Usage Tracking & Limits



| Service | Monthly Limit | How to Monitor || Service | Monthly Limit | How to Monitor |

|---------|---------------|----------------||---------|---------------|----------------|

| NewsAPI | 100 req/day | Dashboard: https://newsapi.org/account || NewsAPI | 100 req/day | Dashboard: https://newsapi.org/account |

| Deepgram STT | 200 minutes | Console: https://console.deepgram.com/ || Deepgram STT | 200 minutes | Console: https://console.deepgram.com/ |

| gTTS | Unlimited | No tracking needed! || gTTS | Unlimited | No tracking needed! |

| Gemini API | Rate-limited | Errors show in logs if exceeded || Gemini API | Rate-limited | Errors show in logs if exceeded |

| Upstash Redis | 10K commands/day | Dashboard: https://console.upstash.com/ || Upstash Redis | 10K commands/day | Dashboard: https://console.upstash.com/ |

| Cloudflare R2 | 10GB storage | Dashboard: https://dash.cloudflare.com/ || Cloudflare R2 | 10GB storage | Dashboard: https://dash.cloudflare.com/ |



------



## 💡 Cost Optimization Tips## 💡 Cost Optimization Tips



1. **Cache aggressively**: Use Redis to cache news (5 min), TTS audio (persistent), verification results (24h)1. **Cache aggressively**: Use Redis to cache news (5 min), TTS audio (persistent), verification results (24h)

2. **Lazy TTS generation**: Only generate audio when user requests it (not preemptively)2. **Lazy TTS generation**: Only generate audio when user requests it (not preemptively)

3. **Audio compression**: gTTS outputs MP3 (smaller than WAV); perfect for IoT3. **Audio compression**: gTTS outputs MP3 (smaller than WAV); perfect for IoT

4. **Batch operations**: Group multiple news requests when possible4. **Batch operations**: Group multiple news requests when possible

5. **Monitor usage**: Set up alerts in each provider's dashboard5. **Monitor usage**: Set up alerts in each provider's dashboard



------



## 🎓 Upgrade Path (When You Get Funding)## 🎓 Upgrade Path (When You Get Funding)



When your project gets traction or funding, here's the smooth upgrade path:When your project gets traction or funding, here's the smooth upgrade path:



| Current (Free) | Upgrade To | Cost | Why Upgrade || Current (Free) | Upgrade To | Cost | Why Upgrade |

|----------------|------------|------|-------------||----------------|------------|------|-------------|

| Deepgram free tier | Deepgram paid | $0.0043/min | More minutes, lower latency || Deepgram free tier | Deepgram paid | $0.0043/min | More minutes, lower latency |

| gTTS | ElevenLabs / Google Cloud TTS | $15-30/1M chars | Better voice quality, custom voices || gTTS | ElevenLabs / Google Cloud TTS | $15-30/1M chars | Better voice quality, custom voices |

| Local/R2 storage | AWS S3 + CloudFront CDN | ~$5-20/mo | Global CDN, faster delivery || Local/R2 storage | AWS S3 + CloudFront CDN | ~$5-20/mo | Global CDN, faster delivery |

| Render free tier | Render standard | $7/mo | No sleep, more resources || Render free tier | Render standard | $7/mo | No sleep, more resources |

| Gemini free tier | Vertex AI | ~$0.50/1K reqs | SLA, rate limits, enterprise features || Gemini free tier | Vertex AI | ~$0.50/1K reqs | SLA, rate limits, enterprise features |



**Total upgrade cost: ~$50-100/month** for professional production deployment**Total upgrade cost: ~$50-100/month** for professional production deployment



------



## 🆘 Troubleshooting## 🆘 Troubleshooting



### "gTTS not installed"### "gTTS not installed"

```powershell```powershell

pip install gTTSpip install gTTS

``````



### "Deepgram API key invalid"### "Deepgram API key invalid"

- Check `.env`: `DEEPGRAM_API_KEY=your_key_here`- Check `.env`: `DEEPGRAM_API_KEY=your_key_here`

- Verify key at https://console.deepgram.com/- Verify key at https://console.deepgram.com/



### "Audio file not found" (local storage)### "Audio file not found" (local storage)

- Ensure `backend/media/` directory exists- Ensure `backend/media/` directory exists

- On Render: Switch to Cloudflare R2 (files persist across deployments)- On Render: Switch to Cloudflare R2 (files persist across deployments)



### "Redis connection failed"### "Redis connection failed"

- Local: Start Redis server- Local: Start Redis server

- Cloud: Check Upstash URL format and credentials- Cloud: Check Upstash URL format and credentials



------



## 📚 Additional Resources## 📚 Additional Resources



- **Deepgram Docs**: https://developers.deepgram.com/docs- **Deepgram Docs**: https://developers.deepgram.com/docs

- **gTTS Documentation**: https://gtts.readthedocs.io/- **gTTS Documentation**: https://gtts.readthedocs.io/

- **Cloudflare R2 Guide**: https://developers.cloudflare.com/r2/- **Cloudflare R2 Guide**: https://developers.cloudflare.com/r2/

- **Upstash Redis**: https://docs.upstash.com/redis- **Upstash Redis**: https://docs.upstash.com/redis

- **Render Deployment**: https://render.com/docs- **Render Deployment**: https://render.com/docs



------



## 🎉 You're All Set!## 🎉 You're All Set!



Your TruthPod backend now runs **100% free** with:Your TruthPod backend now runs **100% free** with:

- ✅ Real speech recognition (200 min/month)- ✅ Real speech recognition (200 min/month)

- ✅ Unlimited text-to-speech- ✅ Unlimited text-to-speech

- ✅ Cloud storage (10GB free)- ✅ Cloud storage (10GB free)

- ✅ News verification- ✅ News verification

- ✅ Analytics & caching- ✅ Analytics & caching



Perfect for student projects, hackathons, and early-stage startups. Scale up when you're ready! 🚀Perfect for student projects, hackathons, and early-stage startups. Scale up when you're ready! 🚀

