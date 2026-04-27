#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────────────────
#   Zyrabit SLM — Build & Verify
#   Usage: ./build_and_verify.sh [--local | --prod]
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

MODE="local"
[[ "${1:-}" == "--prod" ]] && MODE="prod"

COMPOSE_FILES="-f $PROJECT_ROOT/docker-compose.yml"
[[ "$MODE" == "local" ]] && COMPOSE_FILES="$COMPOSE_FILES -f $PROJECT_ROOT/docker-compose.local.yml"

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

MODE_UPPER=$(echo "$MODE" | tr '[:lower:]' '[:upper:]')

# ── Expected containers per mode ──
if [[ "$MODE" == "local" ]]; then
    EXPECTED_CONTAINERS=("zyrabit-api" "zyrabit-web" "zyrabit-engine" "zyrabit-db")
else
    EXPECTED_CONTAINERS=("zyrabit-traefik" "zyrabit-api" "zyrabit-web" "zyrabit-engine" "zyrabit-db" "zyrabit-prometheus" "zyrabit-grafana")
fi

# ─── PHASE 1: BUILD ───
echo -e "\n${BOLD}${BLUE}══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}   🔨 ZYRABIT SLM — BUILD (${MODE_UPPER})                    ${NC}"
echo -e "${BOLD}${BLUE}══════════════════════════════════════════════════${NC}\n"

echo -e "${YELLOW}[1/3] Building Docker images...${NC}"
docker compose $COMPOSE_FILES build --parallel 2>&1 | tail -5

if [[ $? -ne 0 ]]; then
    echo -e "\n${RED}✗ Build failed. Check the output above.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Images built successfully.${NC}\n"

# ─── PHASE 2: START ───
echo -e "${YELLOW}[2/3] Starting containers...${NC}"
docker compose $COMPOSE_FILES up -d

echo -e "${GREEN}✓ Containers launched. Waiting 10s for initialization...${NC}"
sleep 10

# ─── PHASE 3: VERIFY ───
echo -e "\n${BOLD}${BLUE}══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}   🔍 ZYRABIT SLM — VERIFICATION                 ${NC}"
echo -e "${BOLD}${BLUE}══════════════════════════════════════════════════${NC}\n"

echo -e "${YELLOW}[3/3] Checking container status...${NC}\n"

PASS=0
FAIL=0

printf "  ${BOLD}%-25s %-15s %-10s${NC}\n" "CONTAINER" "STATUS" "HEALTH"
printf "  ${CYAN}%-25s %-15s %-10s${NC}\n" "─────────────────────────" "───────────────" "──────────"

for CONTAINER in "${EXPECTED_CONTAINERS[@]}"; do
    STATUS=$(docker inspect --format='{{.State.Status}}' "$CONTAINER" 2>/dev/null || echo "not_found")

    if [[ "$STATUS" == "running" ]]; then
        HEALTH=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}N/A{{end}}' "$CONTAINER" 2>/dev/null)
        printf "  ${GREEN}%-25s %-15s %-10s${NC}\n" "$CONTAINER" "running" "$HEALTH"
        ((PASS++))
    else
        printf "  ${RED}%-25s %-15s %-10s${NC}\n" "$CONTAINER" "$STATUS" "—"
        ((FAIL++))
    fi
done

TOTAL=${#EXPECTED_CONTAINERS[@]}

echo ""
echo -e "  ${BOLD}Result: ${GREEN}${PASS}/${TOTAL} running${NC}"
[[ $FAIL -gt 0 ]] && echo -e "  ${RED}✗ ${FAIL} container(s) not running${NC}"

# ─── API Health Check ───
echo -e "\n${YELLOW}[+] API Health Probe...${NC}"

API_URL="http://localhost:8080/v1/health"
[[ "$MODE" == "prod" ]] && API_URL="https://localhost/v1/health"

MAX_RETRIES=6
for i in $(seq 1 $MAX_RETRIES); do
    if curl -sk -f "$API_URL" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ API is responding at ${API_URL}${NC}"
        curl -sk "$API_URL" 2>/dev/null | python3 -m json.tool 2>/dev/null || true
        break
    fi
    if [[ $i -eq $MAX_RETRIES ]]; then
        echo -e "${RED}✗ API did not respond after ${MAX_RETRIES} attempts.${NC}"
        echo -e "  Check logs: docker compose $COMPOSE_FILES logs -f zyrabit-api"
    else
        echo -e "  ${CYAN}Attempt $i/$MAX_RETRIES — retrying in 5s...${NC}"
        sleep 5
    fi
done

# ─── Summary ───
echo -e "\n${BOLD}${BLUE}══════════════════════════════════════════════════${NC}"
if [[ $FAIL -eq 0 ]]; then
    echo -e "${BOLD}${GREEN}   ✅ BUILD & VERIFY COMPLETE — ALL SYSTEMS GO    ${NC}"
else
    echo -e "${BOLD}${RED}   ⚠️  BUILD COMPLETE — ${FAIL} ISSUE(S) DETECTED     ${NC}"
fi
echo -e "${BOLD}${BLUE}══════════════════════════════════════════════════${NC}"

echo -e "\n${BOLD}Diagnostic Commands:${NC}"
echo -e "  ${CYAN}Logs:${NC}      docker compose $COMPOSE_FILES logs -f zyrabit-api"
echo -e "  ${CYAN}Status:${NC}    docker compose $COMPOSE_FILES ps"
echo -e "  ${CYAN}Restart:${NC}   docker compose $COMPOSE_FILES restart"
echo -e "  ${CYAN}Tear down:${NC} docker compose $COMPOSE_FILES down"
echo ""
