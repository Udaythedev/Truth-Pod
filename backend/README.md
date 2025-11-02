TruthPod backend (MVP skeleton)

This folder contains a minimal FastAPI backend used as a starting point for the TruthPod project.

Quick start (Windows PowerShell):

# Create a virtual environment and install dependencies
python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt

# Run the app (development)
.\.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Run tests
.\.venv\Scripts\pytest -q

Build & run with Docker:

```powershell
# from repo root
cd "d:\Code playground\Hackathons\Truth-Pod\backend"
docker build -t truthpod-backend:local .
docker run --rm -p 8000:8000 truthpod-backend:local
```

Notes:
- The Docker image runs as a non-root user and exposes `/media` for enrolled face images.
- For production, push the image to a registry and deploy to Render/Railway/AWS.

CORS & Logging
---------------
- CORS is enabled and configurable via `ALLOW_ORIGINS` (comma-separated list or `*`).
- Basic logging level is controlled by `LOG_LEVEL` (e.g., `INFO`, `DEBUG`).

Migrations (Alembic)

This project uses Alembic for schema migrations. In development, the app will ensure missing tables exist, but it no longer drops/recreates by default. For production, always run Alembic.

To create and apply migrations locally:

PowerShell example:

```powershell
cd "d:\Code playground\Hackathons\Truth-Pod\backend"
# generate a revision (autogenerates from SQLModel metadata)
.\.venv\Scripts\alembic revision --autogenerate -m "create initial tables"

# apply migrations
.\.venv\Scripts\alembic upgrade head
```

By default the `alembic.ini` points to `sqlite:///./truthpod.db`. To use PostgreSQL locally, set `DATABASE_URL` before running the commands, for example:

```powershell
setx DATABASE_URL "postgresql://user:password@localhost:5432/truthpod_db"
# restart shell or set in process: $env:DATABASE_URL = 'postgresql://...'
```

I added a `docker-compose.yml` that brings up Postgres + Redis for local development. Quick usage:

PowerShell (from `backend`):

```powershell
# start Postgres + Redis
.\run_postgres_redis.ps1

# generate and apply migrations (uses DATABASE_URL environment variable)
# in PowerShell set env for current session and run migrations:
$env:DATABASE_URL = 'postgresql+psycopg2://truthpod:truthpod@localhost:5432/truthpod'
.\.venv\Scripts\alembic upgrade head

# run the backend (points at Postgres/Redis when env vars set)
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The `docker-compose.yml` mounts `./media` into the container so enrolled images are preserved locally.

Production notes (DB)
---------------------
- On deploy, run Alembic migrations as part of your release process:

```powershell
# example (Windows PowerShell, from backend folder with venv active)
.\.venv\Scripts\alembic upgrade head
```

- Dev-only reset: If you need to reset your local DB to match models, set `TRUTHPOD_RESET_DB=1` when starting the app. This flag makes the app drop and recreate tables for the current engine.

```powershell
$env:TRUTHPOD_RESET_DB = '1'
.\.venv\Scripts\uvicorn app.main:app --reload
```

- Recommendation: Use migrations for all schema changes; avoid relying on automatic table creation in production.

Publishing Docker images
------------------------

I added a GitHub Actions workflow that can publish the backend Docker image to GitHub Container Registry (GHCR) on pushes to `main` or `LLM`:

- Workflow: `.github/workflows/publish-image.yml`
- It builds `backend/Dockerfile` and pushes tags `ghcr.io/<OWNER>/truthpod-backend:latest` and `ghcr.io/<OWNER>/truthpod-backend:<commit-sha>`.
- It uses the default `GITHUB_TOKEN` for auth, no additional secrets are required to publish to the same repository's GHCR (make sure package/registry permissions are enabled if your org requires it).

If you'd prefer publishing to Docker Hub or another registry, I can add that workflow instead (it will require repository secrets for credentials).

Provider integration / gated tests
---------------------------------

If you want to run an integration check against a real verification provider (Gemini/Vertex), you can provide credentials as environment variables and run the example script:

PowerShell:

```powershell
# set credentials for current session (example for Vertex)
$env:VERTEX_API_ENDPOINT = 'https://LOCATION-aiplatform.googleapis.com/v1/projects/PROJECT/locations/LOCATION/models/MODEL:predict'
$env:VERTEX_API_KEY = 'your-key'

# or for Gemini-style API
$env:GEMINI_API_URL = 'https://your-gemini-proxy.example.com/verify'
$env:GEMINI_API_KEY = 'your-key'

# run the provider example
python .\scripts\verify_provider_example.py --text "Breaking: local integration test"
```

CI note: the repository includes an optional GitHub Actions job that runs the same example script only when `GEMINI_API_KEY` or `VERTEX_API_KEY` are configured in Actions Secrets. This prevents accidental calls during normal CI runs.

Voice (STT/TTS)
----------------
See `VOICE_PROVIDER.md` for configuring Google Cloud Speech-to-Text and Text-to-Speech.

- Optional reliability knobs: set `VOICE_RETRIES` (default 1) and `VOICE_RETRY_DELAY` seconds (default 0.0) to enable simple retry/backoff around provider calls.

User Preferences
----------------
The backend supports per-user preferences (language, region, news categories):
- `GET /api/iot/preferences/{user_id}` - Get preferences (defaults: language=en, region=in)
- `POST /api/iot/preferences/{user_id}` - Set/update preferences with JSON body: `{"language": "en", "region": "us", "categories": "technology,business"}`

These preferences can be used to personalize news queries and TTS output.

Analytics
---------
Device interaction analytics endpoints:
- `GET /api/iot/analytics/summary` - Get aggregated stats (total interactions, grouped by action type, recent 10)
- `GET /api/iot/analytics/interactions?limit=50&offset=0` - Get paginated interaction logs with details

Both endpoints require valid device authentication.

Background TTS queue/status
---------------------------
The background TTS synthesis request/status flow uses Redis for cross-instance “pending” tracking when `REDIS_URL` is set, and falls back to an in-memory set for development.

- Configure pending TTL via `TTS_PENDING_TTL` seconds (default 300).
- `docker-compose.yml` and `run_postgres_redis.ps1` start a local Redis and set `REDIS_URL` so you can test the background flow with Redis.

Files created:
- `app/main.py` - FastAPI app with health and device register endpoints
- `app/models.py` - SQLModel DB models
- `app/schemas.py` - Pydantic request/response schemas
- `app/database.py` - DB engine & session
- `tests/test_api.py` - basic API tests

Deploy to Render
----------------
This repo includes a Render Blueprint (`render.yaml`) to provision and deploy:
- A web service running the backend from `backend/Dockerfile` (free plan by default)
- A managed Postgres database (`truthpod-db`)
- A managed Redis instance (`truthpod-redis`)

Quick start:
1) Create a new Blueprint in Render and point it at your fork of this repository.
2) On the preview screen, review resources and click Apply.
3) After deploy, the backend is available at your Render service URL; health check at `/api/health`.

Environment variables via Blueprint:
- `DATABASE_URL` and `REDIS_URL` are wired automatically from the managed services.
- Security & ops: `SECRET_KEY` (auto-generated), `LOG_LEVEL`, `ALLOW_ORIGINS`, `HTTPS_ENFORCE`, `TRUST_X_FORWARDED_PROTO`.
- Voice & storage (optional): `GOOGLE_CLOUD_PROJECT`, `GOOGLE_APPLICATION_CREDENTIALS`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`.

Migrations: The container entrypoint automatically runs `alembic upgrade head` when `DATABASE_URL` points to Postgres, so database schema stays up to date on each deploy.

Security and operations
-----------------------
- Token rotation: use `POST /api/iot/device/token/rotate` to issue a new device token; old tokens are rejected automatically.
- Rate limiting (opt-in): set `RATE_LIMIT_ENABLED=1` to enable simple per-IP/device rate limiting. Uses Redis when `REDIS_URL` is set, falls back to in-process.
- HTTPS enforcement: if you’re behind a proxy/ingress that sets `X-Forwarded-Proto`, you can enforce HTTPS by handling termination at the edge and ensuring only HTTPS is exposed. (Middleware hook is prepared; enable per-deploy policy.)
- Monitoring:
	- Sentry: set `SENTRY_DSN` (and optionally `SENTRY_TRACES_SAMPLE_RATE`) to capture errors and traces.
	- Prometheus: if `prometheus_client` is installed, a `/metrics` endpoint is exposed for scraping.

Runtime knobs (env):
- `RATE_LIMIT_ENABLED`: `1` to enable rate limiter dependencies.
- `REDIS_URL`: enables Redis-backed rate limiting and background TTS pending tracking when set.
- `TTS_PENDING_TTL`: TTL (seconds) for pending background jobs (default 300).
- `HTTPS_ENFORCE`: `1` to reject non-HTTPS requests (honors `X-Forwarded-Proto` when `TRUST_X_FORWARDED_PROTO=1`).
- `TRUST_X_FORWARDED_PROTO`: `1` (default) to trust proxy protocol header in HTTPS checks.
- Request ID: every response includes `X-Request-ID`; you can pass your own `x-request-id` header to propagate.

Notes:
- This is intentionally small. Next steps: add more endpoints (trending, search, face, voice), JWT auth middleware, PostgreSQL config, and CI/Docker.
