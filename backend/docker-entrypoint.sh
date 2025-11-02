#!/bin/sh
set -e

echo "==> docker-entrypoint: starting"

# If DATABASE_URL points to Postgres, wait for it to become available and run migrations
if [ -n "$DATABASE_URL" ] && echo "$DATABASE_URL" | grep -qiE "postgres|postgresql"; then
  echo "DATABASE_URL points to Postgres; waiting for DB and running migrations..."
  attempt=0
  max_attempts=30
  until [ "$attempt" -ge "$max_attempts" ]; do
    echo "Checking DB connectivity (attempt $attempt)..."
    python - <<'PY'
import os
from sqlalchemy import create_engine
try:
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise SystemExit(2)
    eng = create_engine(url)
    conn = eng.connect()
    conn.close()
    raise SystemExit(0)
except Exception:
    raise SystemExit(1)
PY
    rc=$?
    if [ "$rc" -eq 0 ]; then
      echo "DB is reachable"
      break
    fi
    attempt=$((attempt+1))
    echo "DB not ready yet; sleeping 2s"
    sleep 2
  done

  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "Timed out waiting for DB after $max_attempts attempts"
  else
    echo "Running alembic upgrade head"
    # run migrations but do not fail the container if migrations error out
    alembic upgrade head || echo "alembic upgrade failed (continuing)"
  fi
fi

echo "==> docker-entrypoint: exec $@"
exec "$@"
