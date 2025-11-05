# Truth-Pod
TruthPod – IoT News Verification Pod

TruthPod is a cloud-first, hardware-efficient IoT system for real-time fake news detection, verified news delivery, and face recognition at home, schools, and offices. Powered by ESP32 devices and a Python/FastAPI/PostgreSQL backend, TruthPod brings reliable news and AI fact-checking to your living room, using your home WiFi and cloud-based services for minimal maintenance and maximum scalability.

Features:
- Voice-activated news search & verification
- AI-powered fake news detection (Gemini or compatible provider)
- Face recognition for personalized news feeds
- Compact ESP32-based hardware (“TruthPod”)
- All data stored securely in the cloud
- RESTful API backend (FastAPI)
- Easy deployment to Render, Railway, Supabase, or AWS

Perfect for: demos, education, makers, media literacy, and smart home innovation.

## Backend — Quick start (PowerShell)

Follow these steps to run the minimal FastAPI backend scaffold locally for development and testing.

1. Open PowerShell and change into the backend folder:

```powershell
cd "d:\Code playground\Hackathons\Truth-Pod\backend"
```

2. Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

3. Copy environment variables and (optionally) edit `.env`:

```powershell
copy .env.example .env
# then edit .env in your editor to set SECRET_KEY or DATABASE_URL if needed
```

4. Run the app (development):

```powershell
.\.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

5. Run tests:

```powershell
.\.venv\Scripts\pytest -q
```

Notes:
- The backend scaffold is intentionally small: health and device registration endpoints are available at `/api/health` and `/api/iot/device/register`.
- For production, switch to PostgreSQL, configure secrets, and add CI/Dockerfiles.

## Developer setup

### Pre-commit hooks (recommended)
Use pre-commit to catch issues like accidental secrets before they land in git.

```powershell
pip install pre-commit
pre-commit install
```

This repo includes a gitleaks hook configured to redact or block potential secret leakage.

### Secret scanning in CI
A GitHub Actions workflow runs gitleaks on pushes and pull requests to `main` and `LLM`.

## Firmware quick notes
- Update WiFi credentials in the sketches.
- The base URL is set to the deployed backend: `https://truth-pod.onrender.com`.
- ESP32-CAM firmware supports enroll/recognize endpoints and stores the device token in Preferences after registration.

## Release process
- Create a tag like `v0.1.0` to trigger the release workflow. It will build and push the Docker image to GHCR and create a GitHub Release.
