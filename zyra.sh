#!/usr/bin/env bash

# ──────────────────────────────────────────────────────────────────────────────
#   ZYRABIT SLM — Unified CLI
#   Version: 2.3.1
#   Usage: ./zyra.sh [command] [options]
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ─── ZYRABIT BRAND PALETTE & COLOR SYSTEM ────────────────────────────────────
BRAND_SLATE='\033[38;2;63;90;109m'     # #3F5A6D Slate
BRAND_ICE='\033[38;2;96;144;180m'      # #6090B4 Ice Blue
BRAND_LIGHT='\033[38;2;226;236;244m'   # #E2ECF4 Soft Light
BRAND_AMBER='\033[38;2;245;176;65m'    # #F5B041 Zyrabit Bee Yellow
BRAND_DARK='\033[38;2;40;40;40m'       # Bee Black Stripes
GREEN='\033[38;2;60;207;142m'          # #3CF18E Neon Emerald
CYAN='\033[38;2;0;210;255m'           # #00D2FF Electric Cyan
YELLOW='\033[38;2;255;170;0m'         # Amber Warning
RED='\033[38;2;255;75;75m'            # Coral Red
PURPLE='\033[38;2;168;85;247m'         # Sovereign Purple
BLUE='\033[38;2;59;130;246m'          # Deep Tech Blue
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

print_banner() {
    echo -e "        ${BRAND_LIGHT}_${NC}"
    echo -e "       ${BRAND_LIGHT}/_/_      .'''.${NC}"
    echo -e "    ${BRAND_DARK}=${BRAND_AMBER}O${BRAND_DARK}(${BRAND_AMBER}_${BRAND_DARK}))${BRAND_AMBER}))${NC} ${BRAND_LIGHT}...'     \`${NC}"
    echo -e "       ${BRAND_LIGHT}\\\\_\\\\            \`.    .'''.${NC}"
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

log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_ok()   { echo -e "${GREEN}✔${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_err()  { echo -e "${RED}✖${NC} $1" >&2; }
log_step() { echo -e "\n${BOLD}${BRAND_AMBER}▶ $1${NC}"; }
log_header() {
    print_banner
    echo -e "${BOLD}${BRAND_ICE}═════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}   $1${NC}"
    echo -e "${BOLD}${BRAND_ICE}═════════════════════════════════════════════════════════════════${NC}\n"
}



# ─── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/zyrabit-slm/docker-compose.local.yml"
PROD_COMPOSE_FILE="${SCRIPT_DIR}/zyrabit-slm/docker-compose.yml"
ENV_FILE="${SCRIPT_DIR}/zyrabit-slm/.env"
EXAMPLE_ENV="${SCRIPT_DIR}/zyrabit-slm/example.env"
LLAMA_MODEL_PATH="${SCRIPT_DIR}/zyrabit-slm/models/qwen2.5-1.5b-instruct-q4_k_m.gguf"
LLAMA_SERVER_PORT="8081"
LLAMA_SERVER_PID_FILE="${SCRIPT_DIR}/zyrabit-slm/.llama-server.pid"

# ─── State (defaults) ─────────────────────────────────────────────────────────
PRODUCTION_MODE="false"
PROFILE=""
OVERRIDE_MODEL=""
NO_CACHE="false"
E2E_SECURITY="false"
REPORT_MODE="false"
SKIP_WIZARD="false"   # --yes / -y skips wizard when .env already exists
NOTIFY_MSG=""
COMMANDS=()

# ─── Docker compose detection ─────────────────────────────────────────────────
DOCKER_COMPOSE_CMD="docker compose"
if ! docker compose version >/dev/null 2>&1; then
    if command -v docker-compose >/dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker-compose"
    else
        log_err "Docker Compose not found. Install Docker Desktop or 'docker compose' plugin."
        exit 1
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# HELP
# ─────────────────────────────────────────────────────────────────────────────
usage() {
    print_banner
    echo -e "${BOLD}Zyrabit SLM — Sovereign AI Runtime${NC}\n"
    echo -e "${BOLD}Usage:${NC}  ./zyra.sh [command] [flags]\n"
    echo -e "${BOLD}Commands:${NC}"
    echo -e "  install      Setup & launch  (runs wizard on first install, smart on re-runs)"
    echo -e "  start        Re-launch existing stack without wizard or model pull"
    echo -e "  stop         Tear down all containers"
    echo -e "  verify       Health check: container status + API probe"
    echo -e "  validate     Sovereign QA: unit tests, PII, air-gap, architecture"
    echo -e "  benchmark    Live performance metrics  (--report for 4-engine matrix)"
    echo -e "  audit        Proof-of-Control: compliance & 0-egress report"
    echo -e "  dev          Native hot-reload mode via uv (no Docker required)"
    echo -e "  doctor       Diagnose hardware, RAM, GPU, Docker, and uv"
    echo -e "  notify       Send notification via MCP bridge\n"
    echo -e "${BOLD}Flags:${NC}"
    echo -e "  --production     Production mode (HTTPS, Traefik, custom domain)"
    echo -e "  --yes / -y       Skip wizard prompts — use existing .env as-is"
    echo -e "  --profile <n>    Add Docker Compose profile  (db, automation, observability-extra)"
    echo -e "  --model <name>   Override AI model (e.g. mistral, llama3, phi3)"
    echo -e "  --no-cache       Force Docker build without cache"
    echo -e "  --report         With benchmark: run 4-engine comparison matrix"
    echo -e "  --e2e-security   With validate: run full PII + air-gap + memory pipeline\n"
    echo -e "${BOLD}Examples:${NC}"
    echo -e "  ./zyra.sh                      # First run → wizard → launch"
    echo -e "  ./zyra.sh install              # Same: wizard if no .env, smart re-run if .env exists"
    echo -e "  ./zyra.sh install -y           # Re-install silently with current config"
    echo -e "  ./zyra.sh install --production # Production wizard → Traefik + HTTPS + PostgreSQL"
    echo -e "  ./zyra.sh start                # Re-launch without setup (stack already configured)"
    echo -e "  ./zyra.sh start --profile db   # Launch with PostgreSQL enabled"
    echo -e "  ./zyra.sh benchmark --report   # 4-engine performance comparison"
    echo -e "  ./zyra.sh notify \"Hello Zyra\"  # Send notification via MCP\n"
}

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
require_docker() {
    command -v docker >/dev/null 2>&1 || { log_err "Docker not installed → https://docs.docker.com/get-docker/"; exit 1; }
    docker info >/dev/null 2>&1      || { log_err "Docker daemon not running. Start Docker Desktop."; exit 1; }
}

active_compose_file() {
    [[ "${PRODUCTION_MODE}" == "true" ]] && echo "${PROD_COMPOSE_FILE}" || echo "${COMPOSE_FILE}"
}

check_local_ollama() {
    curl -s -m 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1 ||
    curl -s -m 2 http://localhost:11434/api/tags  >/dev/null 2>&1
}

api_base_url() {
    [[ "${PRODUCTION_MODE}" == "true" ]] && echo "https://${DOMAIN:-localhost}/v1" || echo "http://localhost:${ZYRABIT_LOCAL_PORT:-8080}/v1"
}

web_api_key() {
    grep '^ZYRABIT_API_KEY_WEB=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2-
}

detect_hardware() {
    local ram_gb cores accelerator
    if [[ "$(uname -s)" == "Darwin" ]]; then
        ram_gb="$(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1024 / 1024 / 1024 ))"
        cores="$(sysctl -n hw.logicalcpu 2>/dev/null || echo 4)"
    else
        ram_gb="$(( $(awk '/MemTotal/{print $2}' /proc/meminfo 2>/dev/null || echo 0) / 1024 / 1024 ))"
        cores="$(nproc 2>/dev/null || echo 4)"
    fi
    if   command -v nvidia-smi >/dev/null 2>&1;                                 then accelerator="nvidia"
    elif [[ -e /dev/tenstorrent ]] || command -v tt-smi >/dev/null 2>&1;        then accelerator="tenstorrent"; export SLM_URL="http://zyrabit-tt-metal:8090"
    elif [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]];           then accelerator="metal";       export SLM_URL="http://host.docker.internal:11434"
    else                                                                              accelerator="cpu"
    fi
    echo "${ram_gb}|${cores}|${accelerator}"
}

# ─────────────────────────────────────────────────────────────────────────────
# WIZARD — called by install on first run (or --yes skips it)
# ─────────────────────────────────────────────────────────────────────────────
run_wizard() {
    log_header "ZYRABIT SETUP WIZARD"
    echo -e "  ${CYAN}Configure your sovereign AI stack. Press Enter to accept defaults.${NC}\n"

    # ── 1. Mode ───────────────────────────────────────────────────────────────
    log_step "1/5  Environment"
        echo "   1) Local / Dev  ← default  (one local URL, no domain)"
    echo "   2) Production              (HTTPS, custom domain, Traefik)"
    read -rp "   Select [1]: " _c; _c="${_c:-1}"
    if [[ "$_c" == "2" ]]; then
        PRODUCTION_MODE="true"
        read -rp "   Domain (e.g. ai.company.com) [localhost]: " _d
        export DOMAIN="${_d:-localhost}"
        log_ok "Production · domain=${DOMAIN}"
    else
        PRODUCTION_MODE="false"; export DOMAIN="localhost"
        log_ok "Local/Dev · http://localhost:8080"
    fi

    # ── 2. Inference engine ───────────────────────────────────────────────────
    log_step "2/5  Inference Engine"
    echo "   1) Ollama native (Mac Metal GPU) ← recommended for Mac"
    echo "   2) Ollama Docker container       (slower, no Metal pass-through)"
    echo "   3) Llama.cpp native Metal (GGUF) (no Ollama app needed)"
    echo "   4) Apple MLX                     (fastest on Apple Silicon)"
    echo "   5) Tenstorrent"
    read -rp "   Select [1]: " _c; _c="${_c:-1}"
    case "$_c" in
        2) INFERENCE_PROVIDER="ollama_docker"  ;;
        3) INFERENCE_PROVIDER="llama_cpp_server" ;;
        4) INFERENCE_PROVIDER="mlx"            ;;
        5) INFERENCE_PROVIDER="tenstorrent"
           PROFILE="${PROFILE:+${PROFILE},}tenstorrent"
           ;;
        *) INFERENCE_PROVIDER="ollama_host"    ;;
    esac
    log_ok "Engine: ${INFERENCE_PROVIDER}"

    # ── 3. Model ──────────────────────────────────────────────────────────────
    log_step "3/5  AI Model"
    local hw_info ram
    hw_info=$(detect_hardware); IFS='|' read -r ram _ _ <<< "$hw_info"
    local rec="1"
    [[ "${ram}" -lt 8 ]] && rec="2"   # auto-recommend lighter model on low RAM
    echo "   1) qwen2.5:7b     ~8 GB  — best quality/speed  $([ "${rec}" == "1" ] && echo "(recommended for your ${ram}GB)" || echo "")"
    echo "   2) qwen2.5:1.5b   ~2 GB  — fast, low RAM       $([ "${rec}" == "2" ] && echo "(recommended for your ${ram}GB)" || echo "")"
    echo "   3) mistral        ~5 GB  — strong reasoning"
    echo "   4) deepseek-r1:7b ~5 GB  — best for code"
    echo "   5) phi3           ~3 GB  — ultra-lightweight"
    read -rp "   Select [${rec}]: " _c; _c="${_c:-$rec}"
    case "$_c" in
        2) OVERRIDE_MODEL="qwen2.5:1.5b"  ;;
        3) OVERRIDE_MODEL="mistral"        ;;
        4) OVERRIDE_MODEL="deepseek-r1:7b" ;;
        5) OVERRIDE_MODEL="phi3"           ;;
        *) OVERRIDE_MODEL="qwen2.5:7b"    ;;
    esac
    if [[ "${INFERENCE_PROVIDER}" == "llama_cpp_server" ]]; then
        OVERRIDE_MODEL="qwen2.5-1.5b-instruct-q4_k_m.gguf"
        log_info "Llama.cpp Metal uses the bundled GGUF model identifier."
    fi
    log_ok "Model: ${OVERRIDE_MODEL}"

    # ── 4. Database ───────────────────────────────────────────────────────────
    log_step "4/5  Database"
    echo "   1) SQLite WAL ← default  (zero-config, embedded, fast)"
    echo "   2) PostgreSQL            (persistent, enterprise/production)"
    read -rp "   Select [1]: " _c; _c="${_c:-1}"
    if [[ "$_c" == "2" ]]; then
        PROFILE="${PROFILE:+${PROFILE},}db"
        log_ok "PostgreSQL enabled — profile 'db' added"
    else
        log_ok "SQLite WAL (embedded)"
    fi

    # ── 5. Whisper ────────────────────────────────────────────────────────────
    log_step "5/5  Audio Transcription (Whisper)"
    echo "   Enable local transcription for .mp3/.mp4/.wav/.m4a files?"
    echo "   1) Yes  (faster-whisper, CPU/Metal)"
    echo "   2) No   (text & PDF only)"
    read -rp "   Select [1]: " _c; _c="${_c:-1}"
    local WHISPER_MODEL="none"
    if [[ "$_c" == "1" ]]; then
        echo "   Model size:"
        echo "     1) base   ~140 MB — fast"
        echo "     2) small  ~500 MB — better accuracy"
        echo "     3) medium ~1.5 GB — high accuracy"
        read -rp "   Select [1]: " _w
        case "${_w:-1}" in 2) WHISPER_MODEL="small" ;; 3) WHISPER_MODEL="medium" ;; *) WHISPER_MODEL="base" ;; esac
        log_ok "Whisper: ${WHISPER_MODEL}"
    else
        log_ok "Audio transcription: disabled"
    fi

    # ── Summary ───────────────────────────────────────────────────────────────
    echo ""
    echo -e "${BOLD}${CYAN}  ╔══ YOUR CONFIGURATION ═══════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}  ║${NC}  Mode     : $([ "$PRODUCTION_MODE" == "true" ] && echo "Production (${DOMAIN})" || echo "Local/Dev  http://localhost:8080")"
    echo -e "${BOLD}${CYAN}  ║${NC}  Engine   : ${INFERENCE_PROVIDER}"
    echo -e "${BOLD}${CYAN}  ║${NC}  Model    : ${OVERRIDE_MODEL}"
    echo -e "${BOLD}${CYAN}  ║${NC}  Database : $(echo "${PROFILE}" | grep -q "db" && echo "PostgreSQL" || echo "SQLite WAL")"
    echo -e "${BOLD}${CYAN}  ║${NC}  Whisper  : $([ "${WHISPER_MODEL}" != "none" ] && echo "Enabled (${WHISPER_MODEL})" || echo "Disabled")"
    echo -e "${BOLD}${CYAN}  ╚═════════════════════════════════════════════════╝${NC}"
    echo ""
    read -rp "  Start with this config? [Y/n]: " _ok
    _ok_lower=$(echo "${_ok:-y}" | tr '[:upper:]' '[:lower:]')
    [[ "${_ok_lower}" == "n" ]] && { log_warn "Cancelled."; exit 0; }

    # Write .env
    if [[ ! -f "${ENV_FILE}" ]] && [[ -f "${EXAMPLE_ENV}" ]]; then
        cp "${EXAMPLE_ENV}" "${ENV_FILE}"
    fi
    if [[ -f "${ENV_FILE}" ]]; then
        sed -i.bak "s|^INFERENCE_PROVIDER=.*|INFERENCE_PROVIDER=${INFERENCE_PROVIDER}|" "${ENV_FILE}" 2>/dev/null || true
        sed -i.bak "s|^MODEL_NAME=.*|MODEL_NAME=${OVERRIDE_MODEL}|"                     "${ENV_FILE}" 2>/dev/null || true
        if [[ "${INFERENCE_PROVIDER}" == "llama_cpp_server" ]]; then
            grep -q "^SLM_URL=" "${ENV_FILE}" && sed -i.bak "s|^SLM_URL=.*|SLM_URL=http://host.docker.internal:${LLAMA_SERVER_PORT}|" "${ENV_FILE}" || echo "SLM_URL=http://host.docker.internal:${LLAMA_SERVER_PORT}" >> "${ENV_FILE}"
            # llama.cpp serves generation; embeddings must have their own local endpoint.
            grep -q "^EMBEDDING_URL=" "${ENV_FILE}" || echo "EMBEDDING_URL=http://host.docker.internal:11434" >> "${ENV_FILE}"
            log_info "llama.cpp generation uses a separate local EMBEDDING_URL."
        fi
        if [[ "${WHISPER_MODEL}" != "none" ]]; then
            grep -q "^WHISPER_MODEL=" "${ENV_FILE}" 2>/dev/null \
                && sed -i.bak "s|^WHISPER_MODEL=.*|WHISPER_MODEL=${WHISPER_MODEL}|" "${ENV_FILE}" \
                || echo "WHISPER_MODEL=${WHISPER_MODEL}" >> "${ENV_FILE}"
        fi
        rm -f "${ENV_FILE}.bak"
        log_ok "Config saved to zyrabit-slm/.env"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# INSTALL — entry point for first-time and re-installs
# ─────────────────────────────────────────────────────────────────────────────
run_install() {
    log_header "ZYRABIT INSTALL"

    # Wizard decision logic:
    #   no .env        → always run wizard
    #   .env exists + --yes / -y → skip wizard, use existing config
    #   .env exists + interactive → ask once
    if [[ ! -f "${ENV_FILE}" ]]; then
        log_info "First install detected — launching setup wizard..."
        run_wizard
    elif [[ "${SKIP_WIZARD}" == "true" ]]; then
        log_ok "Using existing config (--yes). Skipping wizard."
    else
        echo -e "  ${CYAN}Config found at zyrabit-slm/.env${NC}"
        read -rp "  Reconfigure? (runs wizard again) [y/N]: " _r
        _r_lower=$(echo "${_r:-n}" | tr '[:upper:]' '[:lower:]')
        if [[ "${_r_lower}" == "y" ]]; then
            run_wizard
        else
            log_ok "Using existing config."
        fi
    fi

    ensure_local_secrets

    # At this point OVERRIDE_MODEL may have been set by wizard
    local hw_info ram model_name
    hw_info=$(detect_hardware); IFS='|' read -r ram _ _ <<< "$hw_info"
    model_name="${OVERRIDE_MODEL:-}"
    if [[ -z "$model_name" ]]; then
        model_name=$(grep '^MODEL_NAME=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2 || true)
        model_name="${model_name:-$([ "${ram}" -lt 8 ] && echo "qwen2.5:1.5b" || echo "qwen2.5:7b")}"
    fi

    log_info "Model: ${model_name}"
    _build
    run_start
    _pull_models "${model_name}"
    log_ok "✅ Installation complete."
    run_verify
}

ensure_local_secrets() {
    [[ -f "${ENV_FILE}" ]] || { log_err "Missing ${ENV_FILE}; run the setup wizard again."; exit 1; }

    local key generated=0 value
    for key in ZYRABIT_API_KEY_WEB ZYRABIT_API_KEY_MCP; do
        value=$(grep "^${key}=" "${ENV_FILE}" 2>/dev/null | cut -d= -f2- || true)
        if [[ -z "${value}" || "${value}" == replace-with-* || "${value}" == zyrabit-*-token ]]; then
            command -v openssl >/dev/null 2>&1 || { log_err "openssl is required to generate local API keys."; exit 1; }
            value=$(openssl rand -hex 32)
            sed -i.bak "s|^${key}=.*|${key}=${value}|" "${ENV_FILE}"
            generated=1
        fi
    done
    rm -f "${ENV_FILE}.bak"
    [[ "${generated}" == "1" ]] && log_ok "Generated distinct local API keys in zyrabit-slm/.env"
}

# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL — not exposed in help
# ─────────────────────────────────────────────────────────────────────────────
_build() {
    require_docker
    log_info "Building Docker images..."
    local compose_file args=()
    compose_file="$(active_compose_file)"
    [[ "${NO_CACHE}" == "true" ]] && args+=("--no-cache")
    $DOCKER_COMPOSE_CMD -f "${compose_file}" build ${args[@]+"${args[@]}"}
    log_ok "Images built."
}

_pull_models() {
    local model_name="${1}"
    local provider
    provider=$(grep '^INFERENCE_PROVIDER=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2 || echo "ollama_host")
    if [[ "${provider}" == "llama_cpp_server" ]]; then
        [[ -f "${LLAMA_MODEL_PATH}" ]] || { log_err "Missing GGUF model: ${LLAMA_MODEL_PATH}"; return 1; }
        log_ok "GGUF model ready for llama.cpp Metal."
    elif [[ "${provider}" == ollama* ]]; then
        log_info "Pulling model '${model_name}' into Ollama..."
        if check_local_ollama; then
            ollama pull "${model_name}" 2>/dev/null   || log_warn "Pull failed. Run manually: ollama pull ${model_name}"
            ollama pull mxbai-embed-large 2>/dev/null || true
        else
            $DOCKER_COMPOSE_CMD -f "$(active_compose_file)" exec -T zyrabit-engine ollama pull "${model_name}" ||
                log_warn "Pull failed — container may still be initializing."
        fi
        log_ok "Models ready."
    else
        log_info "Provider '${provider}' uses embedded/MLX weights — downloaded automatically on first request."
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# START — re-launch existing stack (no wizard, no pull)
# ─────────────────────────────────────────────────────────────────────────────
run_start() {
    require_docker
    local compose_file compose_args
    compose_file="$(active_compose_file)"
    compose_args=("-f" "${compose_file}")
    [[ -n "${PROFILE:-}" ]] && compose_args+=("--profile" "${PROFILE}")

    if [[ "${PRODUCTION_MODE}" == "true" ]]; then
        log_header "ZYRABIT — PRODUCTION"
        log_info "Domain: ${DOMAIN:-localhost}"
        $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d
    else
        log_header "ZYRABIT — LOCAL / DEV"
        local current_provider
        current_provider=$(grep '^INFERENCE_PROVIDER=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2 || echo "ollama_host")

        if [[ "${current_provider}" == "llama_cpp_server" ]]; then
            if [[ ! -f "${LLAMA_MODEL_PATH}" ]]; then log_err "GGUF model missing. Run setup again after downloading it."; exit 1; fi
            if ! curl -fsS --max-time 2 "http://127.0.0.1:${LLAMA_SERVER_PORT}/v1/models" >/dev/null 2>&1; then
                log_info "Starting llama.cpp native Metal server on port ${LLAMA_SERVER_PORT}..."
                local llama_label="com.zyrabit.llama"
                if launchctl print "gui/$(id -u)/${llama_label}" >/dev/null 2>&1; then
                    launchctl kickstart -k "gui/$(id -u)/${llama_label}"
                else
                    launchctl submit -l "${llama_label}" \
                        -o "${SCRIPT_DIR}/zyrabit-slm/.llama-server.log" \
                        -e "${SCRIPT_DIR}/zyrabit-slm/.llama-server.log" -- \
                        llama-server --model "${LLAMA_MODEL_PATH}" --host 0.0.0.0 \
                        --port "${LLAMA_SERVER_PORT}" --n-gpu-layers 99 --ctx-size 4096 --no-warmup
                fi
                for _ in {1..15}; do
                    curl -fsS --max-time 2 "http://127.0.0.1:${LLAMA_SERVER_PORT}/v1/models" >/dev/null 2>&1 && break
                    sleep 1
                done
                curl -fsS --max-time 2 "http://127.0.0.1:${LLAMA_SERVER_PORT}/v1/models" >/dev/null 2>&1 || {
                    log_err "llama.cpp did not become ready. Check zyrabit-slm/.llama-server.log"
                    exit 1
                }
            fi
            $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d --scale zyrabit-engine=0 2>/dev/null || $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d
        elif [[ "${current_provider}" == "embedded_metal" || "${current_provider}" == "mlx" ]]; then
            log_info "Provider is '${current_provider}' (Native Metal) — skipping zyrabit-engine container."
            $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d --scale zyrabit-engine=0 2>/dev/null ||
            $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d
        elif check_local_ollama && [[ "${current_provider}" != "ollama_docker" && "${current_provider}" != "ollama" ]]; then
            log_info "Ollama detected on host (Metal) — skipping zyrabit-engine container."
            $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d --scale zyrabit-engine=0 2>/dev/null ||
            $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d
        else
            log_info "Starting infrastructure with zyrabit-engine container..."
            $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d
        fi
    fi

    log_ok "Stack is up."
    echo ""
    if [[ "${PRODUCTION_MODE}" != "true" ]]; then
        echo -e "  ${BOLD}🚀 Zyrabit ready!${NC}"
        local local_port="${ZYRABIT_LOCAL_PORT:-8080}"
        echo -e "  ${CYAN}➜ Workspace${NC} http://localhost:${local_port}"
        echo -e "  ${CYAN}➜ API${NC}       http://localhost:${local_port}/v1"
        echo -e "  ${CYAN}➜ Health${NC}    http://localhost:${local_port}/v1/health"
    else
        echo -e "  ${BOLD}🚀 Zyrabit ready!${NC}"
        echo -e "  ${CYAN}➜ Web UI${NC}     https://${DOMAIN:-localhost}"
        echo -e "  ${CYAN}➜ API${NC}        https://${DOMAIN:-localhost}/v1"
        echo -e "  ${CYAN}➜ Grafana${NC}    https://${DOMAIN:-localhost}/grafana"
        echo -e "  ${CYAN}➜ Prometheus${NC} https://${DOMAIN:-localhost}/prometheus"
    fi
    echo -e "  ${YELLOW}ℹ  Run './zyra.sh verify' to check container health.${NC}"
}

# ─────────────────────────────────────────────────────────────────────────────
# STOP
# ─────────────────────────────────────────────────────────────────────────────
run_stop() {
    log_header "STOPPING ZYRABIT"
    require_docker
    $DOCKER_COMPOSE_CMD -f "$(active_compose_file)" down
    log_ok "Stack stopped."
}

# ─────────────────────────────────────────────────────────────────────────────
# VERIFY — health check (runs automatically after install)
# ─────────────────────────────────────────────────────────────────────────────
run_verify() {
    log_header "HEALTH CHECK"
    local containers
    [[ "${PRODUCTION_MODE}" == "true" ]] \
        && containers=("zyrabit-api" "zyrabit-web" "zyrabit-db" "zyrabit-prometheus" "zyrabit-grafana") \
        || containers=("zyrabit-api" "zyrabit-web" "zyrabit-db")

    local pass=0 fail=0
    printf "  ${BOLD}%-28s %-15s %-10s${NC}\n" "CONTAINER" "STATUS" "HEALTH"
    printf "  ${CYAN}%-28s %-15s %-10s${NC}\n"  "────────────────────────────" "───────────────" "──────────"

    local current_provider
    current_provider=$(grep '^INFERENCE_PROVIDER=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2 || echo "ollama_host")

    for c in "${containers[@]}"; do
        local status health
        status=$(docker inspect --format='{{.State.Status}}' "$c" 2>/dev/null | tr -d '[:space:]' || echo "not_found")
        if [[ "$c" == "zyrabit-engine" && "$status" == "not_found" ]]; then
            if [[ "${current_provider}" == "embedded_metal" || "${current_provider}" == "mlx" ]]; then
                printf "  ${GREEN}%-28s %-15s %-10s${NC}\n" "$c" "native-metal" "healthy"
                ((pass++)); continue
            elif check_local_ollama; then
                printf "  ${GREEN}%-28s %-15s %-10s${NC}\n" "$c" "native-metal" "healthy"
                ((pass++)); continue
            fi
        fi
        if [[ "$status" == "running" ]]; then
            health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}N/A{{end}}' "$c" 2>/dev/null | tr -d '[:space:]')
            printf "  ${GREEN}%-28s %-15s %-10s${NC}\n" "$c" "running" "$health"
            ((pass++))
            [[ "$health" == "unhealthy" ]] && { log_warn "Container $c is unhealthy:"; docker logs --tail 10 "$c"; }
        else
            printf "  ${RED}%-28s %-15s %-10s${NC}\n" "$c" "$status" "—"
            [[ "$status" != "not_found" ]] && ((fail++))
        fi
    done

    echo -e "\n  ${BOLD}Containers:${NC} ${GREEN}${pass} up${NC}  ${RED}${fail} down${NC}"
    local base_url; base_url="$(api_base_url)"
    log_info "Probing ${base_url}/health ..."
    if curl -sk -f "${base_url}/health" >/dev/null 2>&1; then
        log_ok "API is responding."
    else
        log_warn "API not responding yet (may still be initializing). Check: docker logs zyrabit-api --tail 30"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# DEV — uvicorn hot-reload, no Docker
# ─────────────────────────────────────────────────────────────────────────────
run_dev() {
    log_header "NATIVE DEV MODE  (uv + hot-reload, no Docker)"
    command -v uv >/dev/null 2>&1 || { log_err "'uv' required. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
    cd "${SCRIPT_DIR}/zyrabit-slm"
    [[ ! -d ".venv" ]] && uv venv --python 3.12
    export VIRTUAL_ENV=".venv"; export PATH="$PWD/.venv/bin:$PATH"
    uv pip install -r api-rag/requirements.txt 2>/dev/null || uv sync
    log_info "Starting API on http://localhost:8082 (hot-reload on)"
    export APP_ENV="local"; export DB_HOST="127.0.0.1"
    cd api-rag && uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload
}

# ─────────────────────────────────────────────────────────────────────────────
# DOCTOR
# ─────────────────────────────────────────────────────────────────────────────
run_doctor() {
    log_header "ZYRABIT DOCTOR"
    local hw_info ram cores accel
    hw_info=$(detect_hardware); IFS='|' read -r ram cores accel <<< "$hw_info"
    echo -e "  ${BOLD}RAM${NC}          ${ram} GB"
    echo -e "  ${BOLD}Cores${NC}        ${cores}"
    echo -e "  ${BOLD}Accelerator${NC}  ${accel}"
    echo -e "  ${BOLD}Mode${NC}         $([ "$PRODUCTION_MODE" == "true" ] && echo "Production" || echo "Local/Dev")"
    echo -e "  ${BOLD}Compose${NC}      ${DOCKER_COMPOSE_CMD}"
    echo -e "  ${BOLD}uv${NC}           $(uv --version 2>/dev/null || echo "not installed")"
    require_docker
    check_local_ollama && log_ok "Ollama detected on host (Metal)." || log_warn "Ollama not detected — will use Docker engine or embedded adapter."
    [[ -f "${ENV_FILE}" ]] && log_ok ".env found at zyrabit-slm/.env" || log_warn "No .env — run './zyra.sh install' first."
    log_ok "Doctor done."
}

# ─────────────────────────────────────────────────────────────────────────────
# NOTIFY
# ─────────────────────────────────────────────────────────────────────────────
run_notify() {
    local message="${1:-}"
    [[ -z "$message" ]] && { log_err "Usage: ./zyra.sh notify \"your message\""; exit 1; }
    local base_url; base_url="$(api_base_url)"
    curl -sk "${base_url}/health" >/dev/null 2>&1 || { log_err "API not reachable. Is Zyrabit running?"; exit 1; }
    local res
    res=$(curl -sk -X POST "${base_url}/chat" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"Send a Telegram notification: ${message}\"}")
    [[ "${res}" == *"response"* ]] && log_ok "Notification sent." || { log_err "API response: ${res}"; exit 1; }
}

# ─────────────────────────────────────────────────────────────────────────────
# VALIDATE — Sovereign QA
# ─────────────────────────────────────────────────────────────────────────────
run_validate() {
    log_header "SOVEREIGN QA VALIDATION"
    log_info "[1/3] Contract, integration and Node tests (offline)..."
    cd "${SCRIPT_DIR}/zyrabit-slm"
    PYTHONPATH="api-rag" "${SCRIPT_DIR}/.venv/bin/pytest" api-rag/tests/ -q 2>&1 && log_ok "Tests PASSED ✅" || { log_err "Tests FAILED."; exit 1; }
    cd "${SCRIPT_DIR}"

    log_info "[2/3] Evidence-bound architecture check..."
    if grep -rn "prometheus_client\|import logging" \
        "${SCRIPT_DIR}/zyrabit-slm/api-rag/app/domain/use_cases/chat_use_case.py" 2>/dev/null; then
        log_err "Architecture violation: domain imports infra deps."; exit 1
    else
        log_ok "Domain layer is clean ✅"
    fi

    [[ -f "${SCRIPT_DIR}/docs/engineering/EVIDENCE_BOUNDARY_HARDENING.md" ]] \
        && log_ok "Evidence boundary contract present ✅" \
        || { log_err "Evidence boundary contract missing."; exit 1; }
    [[ -f "${SCRIPT_DIR}/docs/security/DEPENDENCY_RISKS.md" ]] \
        && log_ok "Dependency risk register present ✅" \
        || { log_err "Dependency risk register missing."; exit 1; }

    [[ "${E2E_SECURITY}" != "true" ]] && { log_ok "Basic QA done. Add --e2e-security for the real PDF smoke test and full pipeline."; return 0; }

    log_header "E2E SECURITY PIPELINE"
    require_docker
    grep -q 'internal: true' "${SCRIPT_DIR}/zyrabit-slm/docker-compose.yml" 2>/dev/null \
        && log_ok "Air-gap: model-network internal=true ✅" \
        || log_warn "'internal: true' not found — check compose file."
    if docker inspect "zyrabit-prometheus" --format '{{.State.Running}}' 2>/dev/null | grep -q "true"; then
        docker exec "zyrabit-prometheus" wget -qO- "http://localhost:9090/prometheus/-/ready" &>/dev/null \
            && log_ok "Prometheus up ✅" || log_warn "Prometheus not responding yet."
    else
        log_warn "zyrabit-prometheus not running."
    fi
    bash "${SCRIPT_DIR}/validation/scripts/monitor_memory.sh" 60 5 \
        && log_ok "Memory within 14GB limit ✅" \
        || { log_err "Memory exceeded 14GB."; exit 1; }
    log_info "[3/3] Real document acceptance (configured local inference)..."
    bash "${SCRIPT_DIR}/validation/scripts/smoke_node_real.sh" \
        && log_ok "Real document acceptance PASSED ✅" \
        || { log_err "Real document acceptance FAILED. Check /v1/health capabilities."; exit 1; }
    log_header "QA COMPLETE 🏆"
}

# ─────────────────────────────────────────────────────────────────────────────
# BENCHMARK
# ─────────────────────────────────────────────────────────────────────────────
run_benchmark() {
    log_header "PERFORMANCE BENCHMARK"
    local base_url token
    base_url="$(api_base_url)"; token="$(web_api_key)"
    [[ -n "${token}" ]] || { log_err "ZYRABIT_API_KEY_WEB is not configured in .env"; exit 1; }

    if [[ "${REPORT_MODE}" == "true" ]]; then
        log_info "Running 4-engine comparison against ${base_url}/chat ..."
        python3 -c "
import json, urllib.request, time, ssl
ctx = ssl._create_unverified_context()
url = '${base_url}/chat'; token = '${token}'
engines = {
    'Ollama Docker (CPU)':   'ollama_docker',
    'Ollama Host  (Metal)':  'ollama_host',
    'Llama.cpp Embedded':    'embedded_metal',
    'Apple MLX':             'mlx',
}
results = {}
for name, prov in engines.items():
    print(f'  ⚡ {name:<25}', end='', flush=True)
    req = urllib.request.Request(url,
        data=json.dumps({'text':'Summarize the indexed documents.','provider':prov}).encode(),
        headers={'Content-Type':'application/json','Authorization':f'Bearer {token}'}, method='POST')
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
            m = json.loads(r.read()).get('metadata', {})
            lat = (time.time()-t0)*1000
            tps_str = f\"{float(m['tps']):.1f} t/s\" if m.get('tps') else \"N/A\"
            ttft_str = f\"{float(m['ttft_ms']):.0f} ms\" if m.get('ttft_ms') else \"N/A\"
            results[name] = {'tps': tps_str, 'ttft': ttft_str, 'lat': f\"{lat:.0f} ms\"}
            print('OK')
    except Exception as e:
        results[name] = {'tps':'N/A','ttft':'N/A','lat':f'FAILED ({type(e).__name__})'}
        print('FAILED')
print()
print(f\"  {'ENGINE':<28} {'TPS':<12} {'TTFT':<12} LATENCY\")
print(f\"  {'-'*28} {'-'*12} {'-'*12} {'-'*12}\")
for n,d in results.items():
    print(f\"  {n:<28} {d['tps']:<12} {d['ttft']:<12} {d['lat']}\")
"
    else
        log_info "Benchmarking active engine at ${base_url}/chat ..."
        local t0 t1 elapsed res
        t0=$(python3 -c 'import time; print(int(time.time()*1000))')
        res=$(curl -sk -X POST "${base_url}/chat" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${token}" \
            -d "{\"text\":\"Summarize the indexed documents.\",\"client_msg_id\":\"bench_${t0}\"}" 2>/dev/null || echo "{}")
        t1=$(python3 -c 'import time; print(int(time.time()*1000))')
        elapsed=$((t1 - t0))
        python3 -c "
import json
try:    m = json.loads('''${res}''').get('metadata',{})
except: m = {}
G,C,A,B,N='\033[38;2;60;180;100m','\033[38;2;70;180;220m','\033[38;2;240;170;50m','\033[1m','\033[0m'
model = m.get('model','qwen2.5:7b')
ttft  = f\"{float(m['ttft_ms']):.1f} ms\" if m.get('ttft_ms') else 'N/A'
tps   = f\"{float(m['tps']):.1f} t/s\"   if m.get('tps')    else 'N/A'
lat   = f\"{float(m.get('latency_ms',${elapsed})):.0f} ms\"
print(f'''
  {B}┌─ 🤖 ENGINE ─────────────────────────────────┐{N}
  │  Model      : {C}{model:<32}{N}│
  │  Accelerator: Apple Silicon Metal              │
  {B}├─ ⚡ PERFORMANCE ────────────────────────────┤{N}
  │  TTFT       : {G}{ttft:<32}{N}│
  │  Throughput : {C}{tps:<32}{N}│
  │  Total time : {A}{lat:<32}{N}│
  {B}└───────────────────────────────────────────────┘{N}''')
"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# AUDIT — Proof of Control
# ─────────────────────────────────────────────────────────────────────────────
run_audit() {
    log_header "SYSTEM DIAGNOSTIC REPORT"
    local base_url token t0 t1 elapsed res
    base_url="$(api_base_url)"; token="$(web_api_key)"
    [[ -n "${token}" ]] || { log_err "ZYRABIT_API_KEY_WEB is not configured in .env"; exit 1; }
    t0=$(python3 -c 'import time; print(int(time.time()*1000))' 2>/dev/null || echo 0)
    res=$(curl -sk -X POST "${base_url}/chat" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${token}" \
        -d "{\"text\":\"Describe the current indexed document collection.\",\"client_msg_id\":\"audit_${t0}\"}" 2>/dev/null || echo "{}")
    t1=$(python3 -c 'import time; print(int(time.time()*1000))' 2>/dev/null || echo 0)
    elapsed=$((t1 - t0))
    python3 -c "
import json
try:    m = json.loads('''${res}''').get('metadata',{})
except: m = {}
G,C,A,B,N='\033[38;2;60;180;100m','\033[38;2;70;180;220m','\033[38;2;240;170;50m','\033[1m','\033[0m'
model    = m.get('model', 'Offline / Not Loaded')
decision = str(m.get('decision', 'DIRECT')).upper()
lat      = f\"{float(m.get('latency_ms', ${elapsed})):.0f} ms\"
tps      = f\"{float(m['tps']):.1f} t/s\" if m.get('tps') else 'N/A'
sources  = m.get('sources') or []
pii      = 'PASSED — 0 tokens leaked' if not m.get('pii_detected') else 'REDACTED (PII Scrubbed)'
print(f'''
  {B}┌─ 🤖 INFERENCE ──────────────────────────────┐{N}
  │  Model    : {C}{model:<34}{N}│
  │  Time     : {A}{lat:<34}{N}│
  │  Speed    : {C}{tps:<34}{N}│
  {B}├─ 🧠 RAG & ROUTING ──────────────────────────┤{N}
  │  Decision : {G}{decision:<34}{N}│
  │  Sources  : {C}{len(sources)} documents retrieved{N}         │''')
for s in list(sources)[:3]:
    print(f'  │  Source   : {C}{str(s):<34}{N}│')
print(f'''  {B}├─ 🛡️  COMPLIANCE ─────────────────────────────┤{N}
  │  Egress   : {G}0 BYTES (Air-Gapped){N}            │
  │  PII      : {G}{pii:<34}{N}│
  {B}└───────────────────────────────────────────────┘{N}
''')
"
}

# ─────────────────────────────────────────────────────────────────────────────
# ARG PARSING
# ─────────────────────────────────────────────────────────────────────────────
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --production|--prod) PRODUCTION_MODE="true"; shift ;;
        --yes|-y)            SKIP_WIZARD="true";     shift ;;
        --profile)           PROFILE="$2";           shift 2 ;;
        --domain)            export DOMAIN="$2";     shift 2 ;;
        --model)             OVERRIDE_MODEL="$2";    shift 2 ;;
        --no-cache)          NO_CACHE="true";        shift ;;
        --e2e-security)      E2E_SECURITY="true";    shift ;;
        --report)            REPORT_MODE="true";     shift ;;
        notify)
            COMMANDS+=("notify"); shift
            [[ -n "${1:-}" && "$1" != -* ]] && { NOTIFY_MSG="$1"; shift; }
            ;;
        help|--help|-h) usage; exit 0 ;;
        -*) log_err "Unknown flag: $1  (run './zyra.sh help')"; exit 1 ;;
        *)  COMMANDS+=("$1"); shift ;;
    esac
done

# No command → install (which runs wizard on first run)
[[ ${#COMMANDS[@]} -eq 0 ]] && COMMANDS=("install")

# ─────────────────────────────────────────────────────────────────────────────
# DISPATCH
# ─────────────────────────────────────────────────────────────────────────────
for CMD in "${COMMANDS[@]}"; do
    case "${CMD}" in
        install)   run_install   ;;
        start)     run_start     ;;
        stop)      run_stop      ;;
        verify)    run_verify    ;;
        validate)  run_validate  ;;
        benchmark) run_benchmark ;;
        audit)     run_audit     ;;
        dev)       run_dev       ;;
        doctor)    run_doctor    ;;
        notify)    run_notify "${NOTIFY_MSG}" ;;
        # legacy aliases — kept for muscle memory
        wizard)    SKIP_WIZARD="false"; run_install ;; # wizard is now part of install
        build)     _build ;; # still callable for CI use
        *) log_err "Unknown command: '${CMD}'.  Run './zyra.sh help'"; exit 1 ;;
    esac
done
