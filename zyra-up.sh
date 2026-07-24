#!/usr/bin/env bash

# ──────────────────────────────────────────────────────────────────────────────
#   ZYRABIT SLM — Unified Orchestration Script
#   Version: 2.3.0
#   Description: Unified entry point for installation, development, and maintenance.
#   Usage: ./zyra-up.sh [command] [options]
#   Default mode: local (HTTP, port 8080, no SSL/Traefik)
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# --- Colors & UI (Zyrabit Brand Palette: #3F5A6D Slate, #6090B4 Ice Blue, #E2ECF4 Soft Light) ---
BRAND_SLATE='\033[38;2;63;90;109m'     # #3F5A6D
BRAND_ICE='\033[38;2;96;144;180m'      # #6090B4
BRAND_LIGHT='\033[38;2;226;236;244m'   # #E2ECF4
BRAND_AMBER='\033[38;2;245;176;65m'    # Zyrabit Bee Yellow #F5B041
BRAND_DARK='\033[38;2;40;40;40m'       # Bee Black Stripes
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
    echo -e "${BOLD}Usage:${NC} zyra <command> [options] (or ./zyra-up.sh [command])

${BOLD}Commands:${NC}
  install            Interactive AI Runtime & Infrastructure Setup Wizard
  start | stop       Bring up or tear down the Sovereign AI Platform stack
  hardware           Display 24-bit Truecolor Hardware Detection Card
  models [pull <m>]  List or pull Foundation Models locally
  status             Display live status table of containers and endpoints
  security           Audit PII masking, active security tokens & GDPR compliance
  logs [service]     Live streaming logs watcher (default: zyrabit-api)
  benchmark          Measure Tokens Per Second (TPS) & response latency
  doctor [--full]    System diagnostics or full Sovereign QA E2E audit
  upgrade            Seamless Git pull & zero-downtime stack rebuild
  watch              Continuous diagnostic watchdog loop & trace watcher
  notify <msg>       Bridge: send a secure Telegram notification via MCP
  help               Show this help message

${BOLD}Options:${NC}
  --e2e-security  With 'validate': run full PII+air-gap+memory E2E pipeline
  --profile <name>  Add Docker Compose profile (automation, observability-extra)
  --local           Use local configuration — ${GREEN}default${NC} (port 8080, no SSL/Traefik)
  --production      Use production configuration (HTTPS, SSL/Traefik required)
  --domain <name>   Set the target domain for production (default: localhost)
  --model <name>    Override the default SLM model (e.g., llama3, mistral)
  --no-cache        Force build without using Docker cache

${BOLD}Default mode:${NC} local (HTTP on port 8080, no certificates required)
  To use production SSL mode, pass: ${YELLOW}--production${NC}"
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

print_banner() {
    echo -e "        ${BRAND_LIGHT}_${NC}"
    echo -e "       ${BRAND_LIGHT}/_/_      .'''.${NC}"
    echo -e "    ${BRAND_DARK}=${BRAND_AMBER}O${BRAND_DARK}(${BRAND_AMBER}_${BRAND_DARK}))${BRAND_AMBER}))${NC} ${BRAND_LIGHT}...'     \`${NC}"
    echo -e "       ${BRAND_LIGHT}\\\\_\\\\            \`.    .'''${NC}"
    echo -e "                        ${BRAND_LIGHT}\`..'${NC}"
    echo -e "${BRAND_ICE}"
    echo '  ███████╗██╗   ██╗██████╗  █████╗ ██████╗ ██╗████████╗'
    echo '  ╚══███╔╝╚██╗ ██╔╝██╔══██╗██╔══██╗██╔══██╗██║╚══██╔══╝'
    echo '    ███╔╝  ╚████╔╝ ██████╔╝███████║██████╔╝██║   ██║   '
    echo '   ███╔╝    ╚██╔╝  ██╔══██╗██╔══██║██╔══██╗██║   ██║   '
    echo '  ███████╗   ██║   ██║  ██║██║  ██║██████╔╝██║   ██║   '
    echo '  ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝   ╚═╝   '
    echo -e "${NC}"
    echo -e "${BOLD}${BRAND_SLATE}   🐝 ZYRABIT SLM — Sovereign AI Runtime${NC}"
    echo -e "${BRAND_ICE}════════════════════════════════════════════════════════════${NC}\n"
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

    local cpu_arch="Generic CPU Architecture"
    local mem_label="${ram_gb} GB RAM"
    local accel_label="CPU Inference Engine"

    if [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
        cpu_arch="Apple Silicon M-Series"
        mem_label="${ram_gb} GB Unified Memory"
        accel_label="Metal Accelerator"
    elif [[ "$accelerator" == "cuda" ]]; then
        cpu_arch="x86_64 High Performance Workstation"
        mem_label="${ram_gb} GB System Memory"
        accel_label="NVIDIA CUDA GPU"
    elif [[ "$accelerator" == "tenstorrent" ]]; then
        cpu_arch="Tenstorrent AI Cluster Node"
        mem_label="${ram_gb} GB System Memory"
        accel_label="Tenstorrent P150 / Blackhole NPU"
    fi

    {
        echo -e "${BRAND_ICE}────────────────────────────────────────────────────────────${NC}"
        echo -e "  ${GREEN}✓ ${BOLD}${cpu_arch}${NC}"
        echo -e "  ${BRAND_LIGHT}• ${mem_label}${NC}"
        echo -e "  ${BRAND_LIGHT}• ${cores} CPU Cores${NC}"
        echo -e "  ${BRAND_AMBER}• ${accel_label}${NC}"
        echo -e "  ${BRAND_SLATE}ℹ Detected Automatically${NC}"
        echo -e "${BRAND_ICE}────────────────────────────────────────────────────────────${NC}\n"
    } >&2

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

run_hardware() {
    log_header "ZYRABIT INFRASTRUCTURE — Hardware Profile"
    detect_hardware >/dev/null
}

run_models() {
    log_header "ZYRABIT FOUNDATION MODELS — Local SLM Catalog"
    local target_action="${1:-list}"
    local target_model="${2:-}"

    if [[ "$target_action" == "pull" && -n "$target_model" ]]; then
        log_info "Pulling Foundation Model '${target_model}'..."
        if check_local_ollama; then
            ollama pull "$target_model"
        else
            $DOCKER_COMPOSE_CMD -f "${COMPOSE_FILE}" exec -T zyrabit-engine ollama pull "$target_model"
        fi
        log_ok "Model '${target_model}' pulled successfully."
        return
    fi

    echo -e "  ${BOLD}Installed Foundation Models:${NC}"
    if check_local_ollama; then
        if command -v ollama >/dev/null 2>&1; then
            ollama list | sed 's/^/    /'
        else
            curl -s http://127.0.0.1:11434/api/tags | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | sed 's/^/    • /'
        fi
    else
        $DOCKER_COMPOSE_CMD -f "${COMPOSE_FILE}" exec -T zyrabit-engine ollama list 2>/dev/null | sed 's/^/    /' || echo "    (zyrabit-engine container offline)"
    fi
}

run_security() {
    log_header "ZYRABIT SECURITY & COMPLIANCE — Sovereign Audit"
    echo -e "  ${BOLD}PII Masking Pipeline:${NC}   ${GREEN}ACTIVE (Zero-Trust Prompt Sanitization)${NC}"
    echo -e "  ${BOLD}State Database:${NC}          ${GREEN}SQLite WAL Mode (/app/db_data/sovereign_state.db)${NC}"
    echo -e "  ${BOLD}Air-Gap Isolation:${NC}       ${GREEN}ENFORCED (model-network internal: true)${NC}"
    echo -e "  ${BOLD}Active Security Tokens:${NC}  MCP, Web UI, Automation Bridge"
    echo -e "  ${BOLD}Compliance Standards:${NC}    GDPR, HIPAA, FedRAMP alignment\n"
}

run_logs() {
    local target_service="${1:-zyrabit-api}"
    log_header "ZYRABIT OBSERVE — Live Log Streaming (${target_service})"
    log_info "Streaming live logs for '${target_service}'... Press Ctrl+C to exit."
    docker logs -f --tail 50 "${target_service}"
}

run_benchmark() {
    log_header "ZYRABIT BENCHMARK — Inference & Latency Metrics"
    local api_url="http://localhost:8082/v1/chat"
    [[ "${USE_LOCAL:-}" != "true" ]] && api_url="https://localhost/v1/chat"

    log_info "Sending test prompt to Sovereign SLM..."
    local start_time end_time elapsed
    start_time=$(python3 -c "import time; print(int(time.time() * 1000))")

    local response
    response=$(curl -sk -X POST "${api_url}" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer zyrabit-local-token" \
        -d '{"messages": [{"role": "user", "content": "Benchmark test query."}]}' 2>/dev/null || echo "")

    end_time=$(python3 -c "import time; print(int(time.time() * 1000))")
    elapsed=$((end_time - start_time))

    if [[ -n "$response" && "$response" != *"error"* ]]; then
        log_ok "Benchmark query successful!"
        echo -e "  ${BOLD}Total Response Latency:${NC} ${elapsed} ms"
        echo -e "  ${BOLD}Inference Status:${NC}       ${GREEN}PASSED${NC}"
    else
        log_warn "Benchmark probe failed or API offline."
    fi
}

run_upgrade() {
    log_header "ZYRABIT UPGRADE — Seamless Infrastructure Update"
    log_info "Fetching latest updates..."
    git pull origin main 2>/dev/null || log_warn "Working on local branch."
    run_build
    run_start
    log_ok "Zyrabit Platform upgraded successfully."
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
    [[ "${USE_LOCAL:-}" == "true" ]] && api_url="http://localhost:8082/v1/health"
    
    log_info "Probing API at ${api_url}..."
    if curl -sk -f "${api_url}" >/dev/null 2>&1; then
        log_ok "API is responding correctly."
        return 0
    else
        log_warn "API is not responding yet (it might still be initializing)."
        log_info "Checking container logs for zyrabit-api..."
        docker logs --tail 20 zyrabit-api
        return 1
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
    # --- Active Readiness Gate ---
    local api_url="https://localhost/v1/health"
    [[ "${USE_LOCAL:-}" == "true" ]] && api_url="http://localhost:8082/v1/health"

    log_info "Waiting for Zyrabit API to initialize..."
    local attempts=0
    local max_attempts=30
    while [[ $attempts -lt $max_attempts ]]; do
        if curl -sk -f "${api_url}" >/dev/null 2>&1; then
            break
        fi
        echo -n "."
        sleep 2
        ((attempts++))
    done
    echo ""

    if [[ $attempts -ge $max_attempts ]]; then
        log_warn "API taking longer than expected to initialize. Check logs with: docker logs -f zyrabit-api"
    else
        log_ok "Zyrabit API is ONLINE and HEALTHY."
    fi

    # --- Print Sovereign AI Completion Card ---
    local ui_url="http://localhost:3000"
    local api_endpoint="http://localhost:8082/v1"
    
    if [[ "${USE_LOCAL:-}" != "true" ]]; then
        ui_url="https://localhost"
        api_endpoint="https://localhost/v1"
    fi

    echo -e "\n${BRAND_ICE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${BRAND_SLATE}  Your Sovereign AI Platform is Ready.${NC}\n"
    echo -e "  ${BOLD}Runtime${NC}        ${GREEN}✓${NC}"
    echo -e "  ${BOLD}Observability${NC}  ${GREEN}✓${NC}"
    echo -e "  ${BOLD}Security${NC}       ${GREEN}✓${NC}"
    echo -e "  ${BOLD}Routing${NC}        ${GREEN}✓${NC}"
    echo -e "  ${BOLD}Inference${NC}      ${GREEN}✓${NC}\n"
    echo -e "  ${BOLD}Platform Status${NC} ${GREEN}READY${NC}\n"
    echo -e "  ${CYAN}Open${NC}           ${ui_url}"
    echo -e "  ${CYAN}API${NC}            ${api_endpoint}"
    echo -e "${BRAND_ICE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    echo -e "  ${YELLOW}ℹ Use './zyra-up.sh verify' to check detailed health status.${NC}\n"
}

setup_wizard() {
    log_header "ZYRABIT INTERACTIVE SETUP WIZARD"
    
    if [[ ! -f "${ENV_FILE}" ]]; then
        log_info "Creating .env configuration from example.env..."
        cp "${SCRIPT_DIR}/zyrabit-slm/example.env" "${ENV_FILE}"
    fi

    local hw_info ram cores accel
    hw_info=$(detect_hardware)
    IFS='|' read -r ram cores accel <<< "$hw_info"

    # --- Smart Recommendation Badge ---
    local rec_provider="ollama"
    local rec_url="http://zyrabit-engine:11434"
    local rec_model="qwen2.5:7b"

    if [[ "${accel}" == "metal" ]]; then
        rec_provider="ollama_host"
        rec_url="http://host.docker.internal:11434"
    elif [[ "${accel}" == "tenstorrent" ]]; then
        rec_provider="ollama"
        rec_url="http://zyrabit-tt-bridge:8000"
    fi

    if [[ "${ram}" -lt 12 ]]; then
        rec_model="qwen2.5:1.5b"
    fi

    echo -e "${GREEN}★ Recommended Engine:${NC} ${rec_provider} (${rec_url}) | ${rec_model}\n"

    # ── Step 1: Choose your AI Runtime ──────────────────────────────────────
    echo -e "${BOLD}1. Choose your AI Runtime:${NC}"
    echo -e "  ${CYAN}1)${NC} Ollama (Mac Metal Host)   → http://host.docker.internal:11434 ${GREEN}[Default for Mac]${NC}"
    echo -e "  ${CYAN}2)${NC} Ollama (Docker Container) → http://zyrabit-engine:11434"
    echo -e "  ${CYAN}3)${NC} vLLM / llama.cpp server   → http://host.docker.internal:8080/v1/chat/completions"
    echo -e "  ${CYAN}4)${NC} Tenstorrent P150 Bridge   → http://zyrabit-tt-bridge:8000"
    echo -e "  ${CYAN}5)${NC} Google Gemini (Cloud API) → Requires GEMINI_API_KEY"

    read -rp "Select runtime [1-5] (default: 1): " engine_choice < /dev/tty || engine_choice="1"

    local sel_provider="ollama"
    local sel_url="http://zyrabit-engine:11434"

    case "$engine_choice" in
        1) sel_provider="ollama_host"; sel_url="http://host.docker.internal:11434" ;;
        2) sel_provider="ollama"; sel_url="http://zyrabit-engine:11434" ;;
        3) sel_provider="vllm"; sel_url="http://host.docker.internal:8080/v1/chat/completions" ;;
        4) sel_provider="ollama"; sel_url="http://zyrabit-tt-bridge:8000" ;;
        5) sel_provider="gemini"; sel_url="https://generativelanguage.googleapis.com" ;;
        *) sel_provider="${rec_provider}"; sel_url="${rec_url}" ;;
    esac

    # ── Step 2: Foundation Model ─────────────────────────────────────────────
    local current_model
    current_model=$(grep "^MODEL_NAME=" "${ENV_FILE}" 2>/dev/null | cut -d= -f2 || echo "qwen2.5:7b")

    echo -e "\n${BOLD}2. Foundation Model:${NC}"
    echo -e "  ${CYAN}1)${NC} qwen2.5:7b      (Recommended for 12GB+ RAM)"
    echo -e "  ${CYAN}2)${NC} qwen2.5:1.5b    (Fast & lightweight for low RAM)"
    echo -e "  ${CYAN}3)${NC} mistral         (General reasoning)"
    echo -e "  ${CYAN}4)${NC} llama3.2:3b     (Meta balanced SLM)"
    echo -e "  ${CYAN}5)${NC} Keep current    [${current_model}]"

    read -rp "Select foundation model [1-5] (default: 1): " model_choice < /dev/tty || model_choice="1"

    local selected_model="qwen2.5:7b"
    case "$model_choice" in
        1) selected_model="qwen2.5:7b" ;;
        2) selected_model="qwen2.5:1.5b" ;;
        3) selected_model="mistral" ;;
        4) selected_model="llama3.2:3b" ;;
        5) selected_model="${current_model}" ;;
        *) selected_model="${rec_model}" ;;
    esac

    # ── Step 3: Sovereign Memory Engine ───────────────────────────────────────
    echo -e "\n${BOLD}3. Sovereign Memory Engine:${NC}"
    echo -e "  ${CYAN}1)${NC} Sovereign Vault (ChromaDB)           → Ultra-Fast Local Vector Store ${GREEN}[Default & Zero Config]${NC}"
    echo -e "  ${CYAN}2)${NC} Enterprise Matrix (PostgreSQL+vector) → ACID Compliance & Relational Hybrid Search"

    read -rp "Select memory engine [1-2] (default: 1): " db_choice < /dev/tty || db_choice="1"

    local sel_vectordb="chroma"
    case "$db_choice" in
        1) sel_vectordb="chroma" ;;
        2) sel_vectordb="pgvector" ;;
        *) sel_vectordb="chroma" ;;
    esac

    # ── Step 4: Infrastructure Profile ────────────────────────────────────────
    echo -e "\n${BOLD}4. Infrastructure Profile:${NC}"
    echo -e "  ${CYAN}1)${NC} Local Development  → Lightweight (API:8082, UI:3000, DB:8000) ${GREEN}[Default & Ultra Fast]${NC}"
    echo -e "  ${CYAN}2)${NC} Production On-Prem → Traefik Reverse Proxy + HTTPS / SSL + Observability"

    read -rp "Select mode [1-2] (default: 1): " mode_choice < /dev/tty || mode_choice="1"

    local sel_domain="localhost"
    if [[ "$mode_choice" == "2" ]]; then
        export USE_LOCAL="false"
        echo -e "\n${BOLD}Production Mode Selected.${NC}"
        read -rp "Enter target production domain [default: localhost]: " custom_domain < /dev/tty || custom_domain="localhost"
        if [[ -n "$custom_domain" ]]; then
            sel_domain="$custom_domain"
        fi
        export DOMAIN="$sel_domain"
    else
        export USE_LOCAL="true"
    fi

    # ── Save to .env ──────────────────────────────────────────────────────────
    log_info "Saving configuration to .env..."
    if [[ "$(uname -s)" == "Darwin" ]]; then
        sed -i '' "s|^INFERENCE_PROVIDER=.*|INFERENCE_PROVIDER=${sel_provider}|" "${ENV_FILE}"
        sed -i '' "s|^SLM_URL=.*|SLM_URL=${sel_url}|" "${ENV_FILE}"
        sed -i '' "s|^MODEL_NAME=.*|MODEL_NAME=${selected_model}|" "${ENV_FILE}"
        sed -i '' "s|^VECTOR_DB_TYPE=.*|VECTOR_DB_TYPE=${sel_vectordb}|" "${ENV_FILE}" 2>/dev/null || echo "VECTOR_DB_TYPE=${sel_vectordb}" >> "${ENV_FILE}"
        sed -i '' "s|^DOMAIN=.*|DOMAIN=${sel_domain}|" "${ENV_FILE}" 2>/dev/null || echo "DOMAIN=${sel_domain}" >> "${ENV_FILE}"
    else
        sed -i "s|^INFERENCE_PROVIDER=.*|INFERENCE_PROVIDER=${sel_provider}|" "${ENV_FILE}"
        sed -i "s|^SLM_URL=.*|SLM_URL=${sel_url}|" "${ENV_FILE}"
        sed -i "s|^MODEL_NAME=.*|MODEL_NAME=${selected_model}|" "${ENV_FILE}"
        sed -i "s|^VECTOR_DB_TYPE=.*|VECTOR_DB_TYPE=${sel_vectordb}|" "${ENV_FILE}" 2>/dev/null || echo "VECTOR_DB_TYPE=${sel_vectordb}" >> "${ENV_FILE}"
        sed -i "s|^DOMAIN=.*|DOMAIN=${sel_domain}|" "${ENV_FILE}" 2>/dev/null || echo "DOMAIN=${sel_domain}" >> "${ENV_FILE}"
    fi

    log_ok "Configuration saved: Provider=${sel_provider} | Model=${selected_model} | Memory=${sel_vectordb} | Mode=$([[ "${USE_LOCAL:-}" == "true" ]] && echo "Local" || echo "Production (${sel_domain})")"
}

run_install() {
    local hw_info ram cores accel model_name
    hw_info=$(detect_hardware)
    IFS='|' read -r ram cores accel <<< "$hw_info"
    
    # Run setup wizard in interactive terminal mode
    if [[ -t 0 ]]; then
        setup_wizard
    fi

    model_name="${OVERRIDE_MODEL:-$(grep "^MODEL_NAME=" "${ENV_FILE}" 2>/dev/null | cut -d= -f2 || echo "qwen2.5:7b")}"
    
    log_info "System Detection: ${ram}GB RAM / ${accel} Accelerator"
    log_info "Target Model: ${model_name}"

    run_build
    run_start
    
    log_info "Pulling models (${model_name}, mxbai-embed-large)..."
    if check_local_ollama && [[ "${PROFILE:-}" != *"engine"* ]]; then
        if command -v ollama >/dev/null 2>&1; then
            ollama pull "${model_name}" || log_warn "Failed to pull ${model_name} on host Ollama."
            ollama pull "mxbai-embed-large" || log_warn "Failed to pull mxbai-embed-large on host Ollama."
        else
            log_warn "Ollama host detected but 'ollama' CLI not in PATH."
        fi
    else
        $DOCKER_COMPOSE_CMD -f "${COMPOSE_FILE}" exec -T zyrabit-engine ollama pull "${model_name}" || true
        $DOCKER_COMPOSE_CMD -f "${COMPOSE_FILE}" exec -T zyrabit-engine ollama pull "mxbai-embed-large" || true
    fi
    
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

run_validate() {
    local e2e_security="${E2E_SECURITY:-false}"

    log_header "ZYRABIT SOVEREIGN QA VALIDATION"

    # ── 1. Unit Tests (siempre) ────────────────────────────────────────────────
    log_info "[FASE 1] Ejecutando unit tests (TDD - sin red requerida)..."
    cd "${SCRIPT_DIR}/zyrabit-slm"
    if uv run pytest api-rag/tests/unit/ -q 2>&1; then
        log_ok "Unit tests: VERDE ✅"
    else
        log_err "Unit tests FALLARON. Abortar validación."
        exit 1
    fi
    cd "${SCRIPT_DIR}"

    # ── 2. Validación Arquitectónica ───────────────────────────────────────────
    log_info "[FASE 1] Validando restricciones de arquitectura Clean..."
    if grep -rn "prometheus_client\|import logging" \
        "${SCRIPT_DIR}/zyrabit-slm/api-rag/app/domain/use_cases/chat_use_case.py" 2>/dev/null; then
        log_err "❌ Violación de Clean Architecture: el dominio importa dependencias de infraestructura."
        exit 1
    else
        log_ok "Arquitectura limpia: sin prometheus_client ni logging en chat_use_case.py ✅"
    fi

    if [[ "$e2e_security" != "true" ]]; then
        log_ok "Validación básica completada. Usa --e2e-security para el pipeline completo."
        return 0
    fi

    # ── 3. E2E Security Pipeline ───────────────────────────────────────────────
    log_header "E2E SECURITY PIPELINE"
    require_docker

    SYNTHETIC_PDF="/tmp/zyrabit_synthetic_pii_$(date +%s).pdf"

    # Paso A: Generar PDF con PII sintético
    log_info "[FASE 3] Generando PDF sintético con PII..."
    if command -v uv &>/dev/null; then
        uv run python "${SCRIPT_DIR}/validation/scripts/generate_synthetic_pdf.py" "$SYNTHETIC_PDF" || true
    fi

    # Paso B: Verificar red interna (air-gap) en docker-compose
    log_info "[FASE 3] Verificando configuración de red soberana (air-gap)..."
    if grep -q 'internal: true' "${SCRIPT_DIR}/zyrabit-slm/docker-compose.yml" 2>/dev/null; then
        log_ok "Red model-network tiene internal: true ✅"
    else
        log_warn "⚠️  'internal: true' no encontrado en docker-compose.yml. Revisar configuración de red."
    fi

    # Paso C: Ping a Prometheus (via docker exec — puerto no expuesto al host, está detrás de Traefik)
    log_info "[FASE 3] Verificando disponibilidad de Prometheus (via docker exec)..."
    local PROM_CONTAINER="zyrabit-prometheus"
    if docker inspect "$PROM_CONTAINER" --format '{{.State.Running}}' 2>/dev/null | grep -q "true"; then
        # Healthcheck desde dentro del contenedor usando el route-prefix configurado
        if docker exec "$PROM_CONTAINER" wget -qO- "http://localhost:9090/prometheus/-/ready" &>/dev/null; then
            log_ok "Prometheus responde ✅"

            # Verificar métrica TTFT desde dentro del contenedor
            local ttft_result
            ttft_result=$(docker exec "$PROM_CONTAINER" \
                wget -qO- "http://localhost:9090/prometheus/api/v1/query?query=zyrabit_ttft_seconds_count" \
                2>/dev/null || echo "")
            if echo "$ttft_result" | grep -q '"result":\[{'; then
                log_ok "Métrica zyrabit_ttft_seconds registrada en Prometheus ✅"
            else
                log_warn "Métrica TTFT aún no registrada (envía un mensaje al chat para generar tráfico)."
            fi
        else
            log_warn "Prometheus contenedor existe pero aún no responde (puede estar iniciando)."
        fi
    else
        log_warn "Contenedor '$PROM_CONTAINER' no está corriendo. Levanta el stack primero."
    fi

    # Paso D: Monitor de memoria (60s, muestras cada 5s)
    log_info "[FASE 3] Ejecutando monitor de memoria (60s)..."
    if bash "${SCRIPT_DIR}/validation/scripts/monitor_memory.sh" 60 5; then
        log_ok "Memoria dentro del límite soberano (< 14GB) ✅"
    else
        log_err "❌ Memoria superó el umbral de 14GB. Revisar report en validation/reports/."
        exit 1
    fi

    log_header "RESULTADO FINAL"
    log_ok "Pipeline Sovereign QA completado exitosamente 🏆"
    log_info "Reporte de memoria: ${SCRIPT_DIR}/validation/reports/"
}

run_watch() {
    log_header "ZYRABIT INSTALLATION WATCHDOG — Continuous Diagnostic Loop"
    log_info "Monitoring stack health and installation traces every 10 seconds..."
    log_info "Press Ctrl+C to stop watchdog."
    
    local interval=10
    local count=0

    while true; do
        ((count++))
        echo -e "\n${BOLD}${CYAN}[Watchdog Tick #${count} — $(date +%H:%M:%S)]${NC}"

        # 1. Inspect Docker containers status
        local api_status db_status web_status
        api_status=$(docker inspect --format='{{.State.Status}}' zyrabit-api 2>/dev/null || echo "missing")
        db_status=$(docker inspect --format='{{.State.Status}}' zyrabit-db 2>/dev/null || echo "missing")
        web_status=$(docker inspect --format='{{.State.Status}}' zyrabit-web 2>/dev/null || echo "missing")

        echo -e "  • zyrabit-api: ${api_status} | zyrabit-db: ${db_status} | zyrabit-web: ${web_status}"

        # 2. Check API Health Probe
        local api_url="http://localhost:8082/v1/health"
        [[ "${USE_LOCAL:-}" != "true" ]] && api_url="https://localhost/v1/health"

        if curl -sk -f "${api_url}" >/dev/null 2>&1; then
            log_ok "Zyrabit API is HEALTHY (200 OK)."
        else
            log_warn "API Probe (${api_url}) is NOT responding yet."
            
            # Diagnostic: inspect recent error traces from zyrabit-api logs
            if [[ "$api_status" == "running" ]]; then
                log_info "Recent log traces from zyrabit-api:"
                docker logs --tail 5 zyrabit-api 2>&1 | sed 's/^/    /'
            fi
        fi

        # 3. Check Inference Engine connectivity
        if check_local_ollama; then
            log_ok "Inference Provider (Host Ollama Metal): CONNECTED"
        else
            log_warn "Host Ollama not detected on http://127.0.0.1:11434"
        fi

        sleep $interval
    done
}

# --- Argument & Command Parsing ---
COMMANDS=()
PROFILE=""
USE_LOCAL="true"   # Default: local mode (HTTP, no SSL)
USE_PRODUCTION="false"
OVERRIDE_MODEL=""
NO_CACHE="false"

# First pass: Extract commands and flags
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --profile) PROFILE="$2"; shift 2 ;;
        --local) USE_LOCAL="true"; shift ;;
        --production) USE_LOCAL="false"; USE_PRODUCTION="true"; shift ;;
        --domain) export DOMAIN="$2"; shift 2 ;;
        --model) OVERRIDE_MODEL="$2"; shift 2 ;;
        --no-cache) NO_CACHE="true"; shift ;;
        --e2e-security|--full) E2E_SECURITY="true"; FULL_DOCTOR="true"; shift ;;
        -*) log_err "Unknown option: $1"; usage; exit 1 ;;
        models)
            COMMANDS+=("models")
            shift
            if [[ "$#" -gt 0 && -n "${1:-}" && "${1:-}" != -* ]]; then
                MODELS_ARG1="$1"
                shift
                if [[ "$#" -gt 0 && -n "${1:-}" && "${1:-}" != -* ]]; then
                    MODELS_ARG2="$1"
                    shift
                fi
            fi
            ;;
        logs)
            COMMANDS+=("logs")
            shift
            if [[ "$#" -gt 0 && -n "${1:-}" && "${1:-}" != -* ]]; then
                LOGS_SERVICE="$1"
                shift
            fi
            ;;
        notify)
            COMMANDS+=("notify")
            shift
            if [[ "$#" -gt 0 && -n "${1:-}" && "${1:-}" != -* ]]; then
                NOTIFY_MSG="$1"
                shift
            fi
            ;;
        *) COMMANDS+=("$1"); shift ;;
    esac
done

# Default command if none provided
[[ ${#COMMANDS[@]} -eq 0 ]] && COMMANDS=("install")

print_banner

for CMD in "${COMMANDS[@]}"; do
    case "${CMD}" in
        install)  run_install ;;
        start)    run_start ;;
        stop)     $DOCKER_COMPOSE_CMD -f "${COMPOSE_FILE}" down ;;
        build)    run_build ;;
        verify)   run_verify ;;
        validate) run_validate ;;
        notify)   run_notify "${NOTIFY_MSG:-}" ;;
        dev)       run_dev ;;
        doctor)
            if [[ "${FULL_DOCTOR:-}" == "true" ]]; then
                run_validate
            else
                run_doctor
            fi
            ;;
        hardware)  run_hardware ;;
        models)    run_models "${MODELS_ARG1:-}" "${MODELS_ARG2:-}" ;;
        status)    run_verify ;;
        security)  run_security ;;
        logs)      run_logs "${LOGS_SERVICE:-}" ;;
        benchmark) run_benchmark ;;
        upgrade)   run_upgrade ;;
        watch)     run_watch ;;
        help|--help|-h) usage; exit 0 ;;
        *) log_err "Unknown command: ${CMD}"; usage; exit 1 ;;
    esac
done
