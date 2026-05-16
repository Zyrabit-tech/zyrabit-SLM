#!/usr/bin/env bash

# ──────────────────────────────────────────────────────────────────────────────
#   ZYRABIT SLM — Unified Orchestration Script
#   Version: 2.0.0
#   Description: Unified entry point for installation, development, and maintenance.
#   Usage: ./zyra-up.sh [command] [options]
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# --- Colors & UI ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# --- Logging Helpers ---
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_ok() { echo -e "${GREEN}✔${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_err() { echo -e "${RED}✖${NC} $1"; }
log_header() {
    echo -e "\n${BOLD}${BLUE}══════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}   $1 ${NC}"
    echo -e "${BOLD}${BLUE}══════════════════════════════════════════════════${NC}\n"
}

# --- Paths & Constants ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/zyrabit-slm/docker-compose.yml"
LOCAL_COMPOSE_FILE="${SCRIPT_DIR}/zyrabit-slm/docker-compose.local.yml"
ENV_FILE="${SCRIPT_DIR}/zyrabit-slm/.env"

# --- Dynamic Command Detection ---
DOCKER_COMPOSE_CMD="docker compose"
if ! docker compose version >/dev/null 2>&1; then
    if command -v docker-compose >/dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker-compose"
    else
        log_err "Neither 'docker compose' nor 'docker-compose' found."
        exit 1
    fi
fi

# --- Helper Functions ---

usage() {
    cat <<EOF
${BOLD}Usage:${NC} ./zyra-up.sh [command] [options]

${BOLD}Commands:${NC}
  install   Full setup: build images, start stack, and pull AI models (default)
  start     Bring up the infrastructure only (no model pulling)
  stop      Tear down the infrastructure
  build     Build Docker images without starting containers
  verify    Health check: validate all containers and API status
  dev       Native local development (starts API via 'uv' with hot-reload)
  doctor    Diagnostic: validate environment, RAM, and hardware acceleration
  notify    Bridge: send a secure Telegram notification via MCP
  help      Show this help message

  --profile <name>  Add Docker Compose profile (automation, observability-extra)
  --local           Use local configuration (port 8080, no SSL/Traefik)
  --domain <name>   Set the target domain for production (default: localhost)
  --model <name>    Override the default SLM model (e.g., llama3, mistral)
  --no-cache        Force build without using Docker cache
EOF
}

require_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        log_err "Docker is not installed."
        exit 1
    fi
    if ! docker info >/dev/null 2>&1; then
        log_err "Docker daemon is not running."
        exit 1
    fi
}

detect_hardware() {
    local ram_gb cores accelerator
    
    # RAM Detection
    if [[ "$(uname -s)" == "Darwin" ]]; then
        ram_gb="$(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1024 / 1024 / 1024 ))"
        cores="$(sysctl -n hw.logicalcpu 2>/dev/null || echo 4)"
    else
        ram_gb="$(( $(awk '/MemTotal/ {print $2}' /proc/meminfo 2>/dev/null || echo 0) / 1024 / 1024 ))"
        cores="$(nproc 2>/dev/null || echo 4)"
    fi

    # Accelerator Detection
    if command -v nvidia-smi >/dev/null 2>&1; then
        accelerator="nvidia"
    elif [[ -e /dev/tenstorrent ]] || command -v tt-smi >/dev/null 2>&1; then
        accelerator="tenstorrent"
        export SLM_URL="http://zyrabit-tt-bridge:8000"
    elif [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
        accelerator="metal"
        export SLM_URL="http://host.docker.internal:11434"
    else
        accelerator="cpu"
    fi

    echo -e "${GREEN}✅ Hardware Profile: ${BOLD}${accelerator^^}${NC} (RAM: ${ram_gb}GB, Cores: ${cores})"
    echo "${ram_gb}|${cores}|${accelerator}"
}

check_local_ollama() {
    # Try both 127.0.0.1 and localhost for maximum compatibility
    if curl -s -m 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1 || \
       curl -s -m 2 http://localhost:11434/api/tags >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

# --- Core Commands ---

run_doctor() {
    log_header "ZYRABIT DOCTOR — System Diagnostics"
    local hw_info
    hw_info=$(detect_hardware)
    IFS='|' read -r ram cores accel <<< "$hw_info"

    echo -e "  ${BOLD}RAM:${NC}          ${ram} GB"
    echo -e "  ${BOLD}Cores:${NC}        ${cores} logical"
    echo -e "  ${BOLD}Accelerator:${NC}  ${accel}"
    echo -e "  ${BOLD}Compose CMD:${NC}  ${DOCKER_COMPOSE_CMD}"
    
    require_docker
    
    if check_local_ollama; then
        log_ok "Local Ollama detected on host (Metal)."
    else
        log_warn "Local Ollama not detected on host. Will use Docker container."
    fi
    
    log_ok "System environment is healthy."
}

run_build() {
    log_header "BUILDING ZYRABIT IMAGES"
    local build_args=()
    [[ "${NO_CACHE:-}" == "true" ]] && build_args+=("--no-cache")
    
    $DOCKER_COMPOSE_CMD -f "${COMPOSE_FILE}" build ${build_args[@]+"${build_args[@]}"}
    log_ok "Build completed successfully."
}

run_verify() {
    log_header "ZYRABIT VERIFICATION — Health Check"
    local containers=("zyrabit-api" "zyrabit-web" "zyrabit-engine" "zyrabit-db")
    local pass=0 fail=0
    
    printf "  ${BOLD}%-25s %-15s %-10s${NC}\n" "CONTAINER" "STATUS" "HEALTH"
    printf "  ${CYAN}%-25s %-15s %-10s${NC}\n" "─────────────────────────" "───────────────" "──────────"

    for c in "${containers[@]}"; do
        local status health
        # Clean potential newlines or spaces from docker output
        status=$(docker inspect --format='{{.State.Status}}' "$c" 2>/dev/null | tr -d '[:space:]' || echo "not_found")
        
        # Special case for engine running on Metal
        if [[ "$c" == "zyrabit-engine" ]] && [[ "$status" == "not_found" ]]; then
            if check_local_ollama; then
                printf "  ${CYAN}%-25s %-15s %-10s${NC}\n" "$c" "native (metal)" "healthy"
                ((pass++))
                continue
            fi
        fi

        if [[ "$status" == "running" ]]; then
            health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}N/A{{end}}' "$c" 2>/dev/null | tr -d '[:space:]')
            printf "  ${GREEN}%-25s %-15s %-10s${NC}\n" "$c" "running" "$health"
            ((pass++))
            
            # If unhealthy, show some logs automatically
            if [[ "$health" == "unhealthy" ]]; then
                log_warn "Container $c is UNHEALTHY. Last logs:"
                docker logs --tail 10 "$c"
            fi
        else
            printf "  ${RED}%-25s %-15s %-10s${NC}\n" "$c" "$status" "—"
            [[ "$status" != "not_found" ]] && ((fail++))
        fi
    done

    echo -e "\n  ${BOLD}Status:${NC} ${GREEN}${pass} active${NC}, ${RED}${fail} inactive${NC}"
    
    # API Probe
    local api_url="https://localhost/v1/health"
    [[ "${USE_LOCAL:-}" == "true" ]] && api_url="http://localhost:8080/v1/health"
    
    log_info "Probing API at ${api_url}..."
    if curl -sk -f "${api_url}" >/dev/null 2>&1; then
        log_ok "API is responding correctly."
    else
        log_warn "API is not responding yet (it might still be initializing)."
        log_info "Checking container logs for zyrabit-api..."
        docker logs --tail 20 zyrabit-api
    fi
}

run_dev() {
    log_header "ZYRABIT NATIVE DEV — (uv + hot-reload)"
    
    if ! command -v uv >/dev/null 2>&1; then
        log_err "'uv' is required for native development. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi

    log_info "Synchronizing Python environment..."
    cd "${SCRIPT_DIR}/zyrabit-slm"
    if [[ ! -d ".venv" ]]; then uv venv --python 3.12; fi
    
    # Source venv and install
    export VIRTUAL_ENV=".venv"
    export PATH="$PWD/.venv/bin:$PATH"
    uv pip install -r api-rag/requirements.txt
    
    log_info "Launching API with hot-reload..."
    export APP_ENV="local"
    export DB_HOST="127.0.0.1"
    cd api-rag && uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
}

run_start() {
    local compose_args=("-f" "${COMPOSE_FILE}")
    [[ "${USE_LOCAL:-}" == "true" ]] && compose_args+=("-f" "${LOCAL_COMPOSE_FILE}")
    [[ -n "${PROFILE:-}" ]] && compose_args+=("--profile" "${PROFILE}")
    
    if check_local_ollama && [[ "${PROFILE:-}" != *"engine"* ]]; then
        log_info "Using native Ollama (host). Skipping zyrabit-engine container..."
        # If we detect local Ollama, we don't start the engine service
        $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d --scale zyrabit-engine=0
    else
        log_info "Launching full infrastructure..."
        $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d
    fi
    log_ok "Infrastructure is up."

    # --- Print Service URLs ---
    echo -e "\n${BOLD}🚀 Zyrabit SLM is ready! Access your services below:${NC}"
    if [[ "${USE_LOCAL:-}" == "true" ]]; then
        echo -e "  ${CYAN}➜ Web UI:${NC}   http://localhost:3000"
        echo -e "  ${CYAN}➜ API:${NC}      http://localhost:8080/v1"
        echo -e "  ${CYAN}➜ DB Admin:${NC} http://localhost:8000/api/v2/heartbeat"
        echo -e "  ${CYAN}➜ Grafana:${NC}  http://localhost:3001"
    else
        echo -e "  ${CYAN}➜ Web UI:${NC}   https://localhost"
        echo -e "  ${CYAN}➜ API:${NC}      https://localhost/v1"
        echo -e "  ${CYAN}➜ Grafana:${NC}  https://localhost/grafana"
        echo -e "  ${CYAN}➜ Prom:${NC}     https://localhost/prometheus"
    fi
    echo -e "  ${YELLOW}ℹ Use './zyra-up.sh verify' to check detailed health status.${NC}\n"
}

run_install() {
    local hw_info ram cores accel model_name
    hw_info=$(detect_hardware)
    IFS='|' read -r ram cores accel <<< "$hw_info"
    
    # Intelligence: select model based on RAM
    model_name="${OVERRIDE_MODEL:-qwen2.5:7b}"
    if [[ "${ram}" -lt 12 ]]; then model_name="qwen2.5:1.5b"; fi
    
    log_info "System Detection: ${ram}GB RAM / ${accel} Accelerator"
    log_info "Target Model: ${model_name}"

    run_build
    run_start
    
    log_info "Pulling models into engine..."
    $DOCKER_COMPOSE_CMD -f "${COMPOSE_FILE}" exec -T zyrabit-engine ollama pull "${model_name}"
    $DOCKER_COMPOSE_CMD -f "${COMPOSE_FILE}" exec -T zyrabit-engine ollama pull "mxbai-embed-large"
    
    log_ok "Installation complete."
    run_verify
}

run_notify() {
    local message="$1"
    if [[ -z "$message" ]]; then
        log_err "Please provide a message. Example: ./zyra-up.sh notify \"Hello Kai\""
        exit 1
    fi

    log_info "Sending sovereign notification via Bridge..."
    
    # Determine API URL based on mode
    local api_url="http://localhost:8080/v1/chat"
    if [[ "${USE_LOCAL}" != "true" ]]; then
        api_url="https://localhost/v1/chat"
    fi

    # Quick health check
    if ! curl -s --insecure "${api_url/chat/health}" > /dev/null; then
        log_err "Core API is not reachable at ${api_url/chat/health}. Is Zyrabit running?"
        exit 1
    fi

    local response
    response=$(curl -s -k -X POST "${api_url}" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"Send a Telegram notification with this exact content: ${message}\"}")

    if [[ "${response}" == *"Error"* ]]; then
        log_err "Failed to dispatch notification. Response: ${response}"
        exit 1
    elif [[ "${response}" == *"response"* ]]; then
        log_ok "Notification dispatched successfully."
    else
        log_err "Unknown API response: ${response}"
        exit 1
    fi
}

# --- Argument & Command Parsing ---
COMMANDS=()
PROFILE=""
USE_LOCAL="false"
OVERRIDE_MODEL=""
NO_CACHE="false"

# First pass: Extract commands and flags
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --profile) PROFILE="$2"; shift 2 ;;
        --local) USE_LOCAL="true"; shift ;;
        --domain) export DOMAIN="$2"; shift 2 ;;
        --model) OVERRIDE_MODEL="$2"; shift 2 ;;
        --no-cache) NO_CACHE="true"; shift ;;
        -*) log_err "Unknown option: $1"; usage; exit 1 ;;
        notify)
            COMMANDS+=("notify")
            shift
            if [[ -n "$1" && "$1" != -* ]]; then
                NOTIFY_MSG="$1"
                shift
            fi
            ;;
        *) COMMANDS+=("$1"); shift ;;
    esac
done

# Default command if none provided
[[ ${#COMMANDS[@]} -eq 0 ]] && COMMANDS=("install")

for CMD in "${COMMANDS[@]}"; do
    case "${CMD}" in
        install) run_install ;;
        start)   run_start ;;
        stop)    $DOCKER_COMPOSE_CMD -f "${COMPOSE_FILE}" down ;;
        build)   run_build ;;
        verify)  run_verify ;;
        notify)  run_notify "${NOTIFY_MSG:-}" ;;
        dev)     run_dev ;;
        doctor)  run_doctor ;;
        help|--help|-h) usage; exit 0 ;;
        *) log_err "Unknown command: ${CMD}"; usage; exit 1 ;;
    esac
done
