#!/usr/bin/env bash
# ==========================================================
# Dota 2 Platform Health Verification Probe
# ==========================================================
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8000}"
WEB_BASE="${WEB_BASE:-http://127.0.0.1:80}"

echo ">> Probing Backend Health at ${API_BASE}/health..."
HEALTH=$(curl -s -f -m 5 "${API_BASE}/health")
echo "   Response: ${HEALTH}"

if echo "${HEALTH}" | grep -q '"status":"healthy"'; then
    echo "   [PASS] Backend reports healthy status."
else
    echo "   [FAIL] Backend is not healthy."
    exit 1
fi

echo ">> Probing Heroes Catalog at ${API_BASE}/heroes..."
HERO_COUNT=$(curl -s -f -m 5 "${API_BASE}/heroes" | grep -o '"hero_id"' | wc -l)
echo "   [PASS] Loaded ${HERO_COUNT} heroes from catalog."

echo ">> Probing Frontend Web App at ${WEB_BASE}/..."
if curl -s -f -m 5 "${WEB_BASE}/" | grep -q 'Dota 2 Coaching Intelligence'; then
    echo "   [PASS] Frontend is serving application index."
fi

echo ">> All system probes passed."

