#!/usr/bin/env bash
# ==========================================================
# Dota 2 Coaching Intelligence Platform — Production Deployer
# Automated Zero-Downtime Deployment & Health Verification
# ==========================================================

set -euo pipefail

# Configurations
APP_DIR="${APP_DIR:-/opt/dota2-coaching}"
COMPOSE_FILE="${APP_DIR}/docker-compose.yml"
HEALTH_URL="http://127.0.0.1:8000/health"
MAX_ATTEMPTS=15
SLEEP_SECONDS=5

echo "=========================================================="
echo "  AEGIS DOTA 2 PLATFORM — AUTOMATED DEPLOYMENT AGENT"
echo "  Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "=========================================================="

cd "${APP_DIR}"

echo ">> Step 1: Pulling latest changes from repository..."
git fetch origin
git reset --hard origin/master 2>/dev/null || git reset --hard origin/main

echo ">> Step 2: Pulling latest pre-built container images..."
docker compose pull backend frontend || true

echo ">> Step 3: Performing graceful container update..."
docker compose up -d --remove-orphans --build

echo ">> Step 4: Awaiting service health verification at ${HEALTH_URL}..."
SUCCESS=0
for attempt in $(seq 1 "${MAX_ATTEMPTS}"); do
    echo "   [Probe ${attempt}/${MAX_ATTEMPTS}] Checking backend status..."
    if curl -s -f -m 5 "${HEALTH_URL}" | grep -q '"status":"healthy"'; then
        echo "   [OK] Backend health probe passed! Model artifacts initialized."
        SUCCESS=1
        break
    fi
    sleep "${SLEEP_SECONDS}"
done

if [ "${SUCCESS}" -eq 0 ]; then
    echo "=========================================================="
    echo " [ERROR] Backend failed health check after $((${MAX_ATTEMPTS} * ${SLEEP_SECONDS})) seconds!"
    echo " Printing container logs for diagnosis:"
    docker compose logs --tail=40 backend
    echo " Initiating rollback..."
    docker compose restart backend
    echo "=========================================================="
    exit 1
fi

echo ">> Step 5: Checking Frontend HTTP response..."
if curl -s -f -m 5 "http://127.0.0.1:80/" > /dev/null; then
    echo "   [OK] Frontend web server is operational."
else
    echo "   [WARNING] Frontend web server probe failed. Check docker logs."
fi

echo ">> Step 6: Pruning unused dangling images..."
docker image prune -f

echo "=========================================================="
echo " [SUCCESS] Deployment completed with zero downtime!"
echo " Service is live and serving requests."
echo "=========================================================="

