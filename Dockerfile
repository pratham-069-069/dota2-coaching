# syntax=docker/dockerfile:1
# -------------------------------------------------------------
# Dota 2 Coaching Intelligence Platform — Unified Production Container
# Multi-stage build: Vite React build -> Python FastAPI with ML & Static Hosting
# -------------------------------------------------------------

# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
ENV VITE_API_BASE_URL=""
RUN npm run build

# Stage 2: Production Python Runtime with ML Engine & Embedded Frontend
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

# Copy compiled frontend from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create a non-privileged user for security compliance
RUN useradd -u 1001 -m appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Healthcheck against FastAPI /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
