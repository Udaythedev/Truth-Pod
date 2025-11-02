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

Migrations (Alembic)

This project includes an Alembic scaffold. To create and apply migrations locally:

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

Files created:
- `app/main.py` - FastAPI app with health and device register endpoints
- `app/models.py` - SQLModel DB models
- `app/schemas.py` - Pydantic request/response schemas
- `app/database.py` - DB engine & session
- `tests/test_api.py` - basic API tests

Notes:
- This is intentionally small. Next steps: add more endpoints (trending, search, face, voice), JWT auth middleware, PostgreSQL config, and CI/Docker.
