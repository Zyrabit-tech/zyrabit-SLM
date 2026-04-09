#!/bin/bash

# Zyrabit Start Script - Unified Launcher
# Usage: ./sh_start.sh [--local | --prod]

MODE="local"
if [[ "$1" == "--prod" ]]; then
    MODE="prod"
fi

COMPOSE_FILES="-f zyrabit-brain-api/docker-compose.yml"
if [[ "$MODE" == "local" ]]; then
    COMPOSE_FILES="$COMPOSE_FILES -f zyrabit-brain-api/docker-compose.local.yml"
fi

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

MODE_UPPER=$(echo "$MODE" | tr '[:lower:]' '[:upper:]')

echo -e "${BOLD}${BLUE}==================================================${NC}"
echo -e "${BOLD}${CYAN}   🚀 ZYRABIT SLM - STARTING IN ${MODE_UPPER} MODE   ${NC}"
echo -e "${BOLD}${BLUE}==================================================${NC}"

# Start Containers
echo -e "\n${YELLOW}[+] Launching Docker containers...${NC}"
docker compose $COMPOSE_FILES up -d --build

echo -e "\n${GREEN}[+] System is initializing...${NC}"
sleep 2

# Output URL Table
echo -e "\n${BOLD}${CYAN}──────────────────────────────────────────────────${NC}"
echo -e "${BOLD}       INTERFACE           |       URL            ${NC}"
echo -e "${BOLD}${CYAN}──────────────────────────────────────────────────${NC}"

if [[ "$MODE" == "local" ]]; then
    echo -e " ${GREEN}Main Web Console${NC}      |  http://localhost:3000"
    echo -e " ${GREEN}API RAG Health${NC}        |  http://localhost:8080/v1/health"
    echo -e " ${YELLOW}Traefik Dashboard${NC}     |  http://localhost:8081/dashboard/"
else
    echo -e " ${GREEN}Main Web Console${NC}      |  https://localhost/"
    echo -e " ${GREEN}API RAG Health${NC}        |  https://localhost/v1/health"
fi

echo -e " ${BLUE}Prometheus${NC}            |  https://localhost/prometheus"
echo -e " ${BLUE}Grafana Dashboards${NC}    |  https://localhost/grafana"
echo -e "${BOLD}${CYAN}──────────────────────────────────────────────────${NC}"

echo -e "\n${BOLD}${WHITE}🛠  DIAGNOSTIC COMMANDS:${NC}"
echo -e " ${CYAN}Check Status:${NC}   ./zyrabit-brain-api/scripts/check_status.sh"
echo -e " ${CYAN}Follow Logs:${NC}    docker compose $COMPOSE_FILES logs -f api-rag"
echo -e " ${CYAN}Full Restart:${NC}   docker compose $COMPOSE_FILES restart"

echo -e "\n${BOLD}${BLUE}==================================================${NC}"
echo -e "${GREEN}Build complete. Give Ollama ~30s to load models.${NC}"
