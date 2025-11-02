# Start Postgres and Redis for local development via docker-compose
param()

Write-Host "Starting Postgres + Redis via docker-compose..."
docker compose up -d

Write-Host "Waiting for Postgres to accept connections (10s)..."
Start-Sleep -Seconds 10

Write-Host "You can run migrations with: .\.venv\Scripts\alembic upgrade head"
Write-Host "Or run the backend locally with: .\.venv\Scripts\python -m uvicorn app.main:app --reload"
