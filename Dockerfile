# syntax=docker/dockerfile:1
# -------------------------------------------------------------
# Dota 2 Coaching Intelligence Platform — Backend Dockerfile
# Production-ready multi-stage Python container
# -------------------------------------------------------------

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

# Install runtime dependencies (libgomp for XGBoost OpenMP acceleration, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (leveraging Docker layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ML model artifacts, feature store, and essential metadata
COPY models/ ./models/
COPY data/features/ ./data/features/
COPY data/raw/hero_names.csv ./data/raw/hero_names.csv
COPY data/raw/player_ratings.csv ./data/raw/player_ratings.csv

# Copy source code and test suite
COPY src/ ./src/
COPY tests/ ./tests/

# Create a non-privileged user for security compliance
RUN useradd -u 1001 -m appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck against FastAPI /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

