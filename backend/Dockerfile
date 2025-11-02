FROM python:3.10-slim

# Use a non-root user for security
ENV APP_USER=truthpod
ENV APP_HOME=/app

WORKDIR ${APP_HOME}

# Install build deps, create user, clean up apt cache
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends build-essential ca-certificates; \
    groupadd -r ${APP_USER} && useradd -r -g ${APP_USER} -d ${APP_HOME} -s /sbin/nologin ${APP_USER}; \
    rm -rf /var/lib/apt/lists/*

# Copy and install requirements in one layer
COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy only what we need
COPY app ./app
COPY tests ./tests
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# Create media directory and give ownership to non-root user
RUN mkdir -p /app/media && chown -R ${APP_USER}:${APP_USER} /app/media /app
RUN chmod +x /usr/local/bin/docker-entrypoint.sh && chown ${APP_USER}:${APP_USER} /usr/local/bin/docker-entrypoint.sh

ENV PYTHONUNBUFFERED=1

USER ${APP_USER}

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
