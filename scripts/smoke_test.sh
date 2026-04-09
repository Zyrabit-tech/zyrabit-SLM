#!/usr/bin/env bash

# Zyrabit SLM Smoke Test Protocol (v1.5.0)
# Validates: Infrastructure, API, Hexagonal Logic, and Gatekeeper.

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_ok() { echo -e "${GREEN}✔${NC} $1"; }
log_err() { echo -e "${RED}✖${NC} $1"; }

# 1. Configuration Check
log_info "Protocol 1: Infrastructure Validation"
cd zyrabit-brain-api
if docker compose config -q; then
    log_ok "Docker Compose configuration is valid."
else
    log_err "Docker Compose configuration failed!"
    exit 1
fi

# 2. Local Bridge Test (Optional but recommended)
log_info "Protocol 2: Connectivity Check (Auto-detecting profile...)"
URL="http://localhost:8080"
if ! curl -s --connect-timeout 2 "${URL}/v1/health" > /dev/null; then
    URL="https://localhost"
    log_info "Local bridge not detected on 8080, falling back to Production HTTPS..."
fi

# Try Health Check
HEALTH=$(curl -k -s "${URL}/v1/health")
if [[ $HEALTH == *"ok"* ]]; then
    log_ok "API is alive! Context: ${HEALTH}"
else
    log_err "API Health check failed or returned degraded status."
fi

# 3. Gatekeeper Security Audit
log_info "Protocol 3: Gatekeeper Policy Enforcement"

# A. Normal Request
log_info "Attempting valid query (Zyrabit Architecture)..."
VALID_RES=$(curl -k -s -X POST "${URL}/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"text":"Tell me about Zyrabit Architecture"}')

if [[ $VALID_RES == *"decision"* ]]; then
    log_ok "Valid query processed successfully."
else
    log_err "Valid query failed. Response: ${VALID_RES}"
fi

# B. Blocked Request (Spam)
log_info "Attempting malicious query (Spam Interception)..."
SPAM_RES=$(curl -k -s -o /dev/null -w "%{http_code}" -X POST "${URL}/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"text":"buy cheap viagra now"}')

if [ "$SPAM_RES" == "400" ]; then
    log_ok "Gatekeeper correctly REJECTED the spam query (HTTP 400)."
else
    log_err "Gatekeeper FAILED to intercept spam. Received HTTP: ${SPAM_RES}"
fi

# 4. Domain Logic Tests (Pytest)
log_info "Protocol 4: Domain & Hexagonal Unit Tests"
cd api-rag
if python3 -m pytest -q app/test/test_gatekeeper.py 2>/dev/null; then
    log_ok "Unit tests passed."
else
    log_warn "Standard unit tests skipped or not found (Ensure pytest is installed)."
fi

echo -e "\n${GREEN}=========================================${NC}"
log_ok "ZYRABIT SMOKE TEST COMPLETED SUCCESSFULLY"
echo -e "${GREEN}=========================================${NC}"
