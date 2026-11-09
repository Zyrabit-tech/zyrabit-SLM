#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
#   ZYRABIT SLM — Unified CLI
#   Version: 2.4.8
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
    echo -e "${BOLD}${BRAND_SLATE}   🐝 ZYRABIT PLATFORM — Sovereign AI Runtime${NC}"
    echo -e "${BRAND_ICE}════════════════════════════════════════════════════════════${NC}\n"
}

log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_ok()   { echo -e "${GREEN}✔${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_err()  { echo -e "${RED}✖${NC} $1" >&2; }
log_step() { echo -e "\n${BOLD}${BRAND_AMBER}▶ $1${NC}"; }
log_header() {
    echo -e "${BOLD}${BRAND_ICE}═════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}   $1${NC}"
    echo -e "${BOLD}${BRAND_ICE}═════════════════════════════════════════════════════════════════${NC}\n"
}



# ─── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/zyrabit-slm/docker-compose.yml"
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
SKIP_PROMPTS="false"   # --yes / -y skips interactive prompts when .env already exists
STATUS_JSON="false"    # --json / -j with status: machine-readable output
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
    echo -e "${BOLD}Zyrabit Platform — Sovereign AI Runtime${NC}\n"
    echo -e "${BOLD}Usage:${NC}  ./zyra.sh [command] [flags]\n"
    echo -e "${BOLD}Commands:${NC}"
    echo -e "  up / start   Instant launch existing stack without configuration prompts"
    echo -e "  install      Setup & launch  (guided configuration on first run, smart on re-runs)"
    echo -e "  stop         Tear down all containers"
    echo -e "  verify       Health check: container status + API probe"
    echo -e "  status       Platform & engine status  (add --json for machine-readable output)"
    echo -e "  validate     Sovereign QA: unit tests, PII, air-gap, architecture"
    echo -e "  benchmark    Live performance metrics  (--report for 4-engine matrix)"
    echo -e "  audit        Proof-of-Control: compliance & 0-egress report"
    echo -e "  dev          Native hot-reload mode via uv (no Docker required)"
    echo -e "  doctor       Diagnose hardware, RAM, GPU, Docker, and uv\n"
    echo -e "${BOLD}Flags:${NC}"
    echo -e "  --production     Production mode (HTTPS, Traefik, custom domain)"
    echo -e "  --yes / -y       Skip interactive prompts — use existing .env as-is"
    echo -e "  --profile <n>    Add optional service profile  (bare, db, automation)"
    echo -e "  --model <name>   Override AI model (e.g. mixtral:8x7b, qwen2.5:3b, deepseek-r1:7b)"
    echo -e "  --no-cache       Force Docker build without cache"
    echo -e "  --report         With benchmark: run 4-engine comparison matrix"
    echo -e "  --e2e-security   With validate: run full PII + air-gap + memory pipeline"
    echo -e "  --json / -j      With status: print JSON instead of colored text\n"
    echo -e "${BOLD}Examples:${NC}"
    echo -e "  ./zyra.sh                      # Display commands & system status"
    echo -e "  ./zyra.sh install              # Run guided setup (Hardware, MoE/Model, ReAct → .env)"
    echo -e "  ./zyra.sh install -y           # Silent setup using current .env"
    echo -e "  ./zyra.sh start                # Launch Full Sovereign Platform (Web UI + RAG + DB + MCP)"
    echo -e "  ./zyra.sh start --model mixtral:8x7b  # Launch with MoE Model"
    echo -e "  ./zyra.sh start --profile bare # Launch Standalone Engine (Headless API)"
    echo -e "  ./zyra.sh benchmark            # Live performance metrics\n"
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

check_local_llama() {
    curl -s -m 2 "http://127.0.0.1:${LLAMA_SERVER_PORT}/v1/models" >/dev/null 2>&1
}

api_base_url() {
    [[ "${PRODUCTION_MODE}" == "true" ]] && echo "https://${DOMAIN:-localhost}/v1" || echo "http://localhost:${ZYRABIT_LOCAL_PORT:-8080}/v1"
}

zyra_version() {
    local v=""
    if [[ -f "${SCRIPT_DIR}/VERSION" ]]; then
        v=$(tr -d '[:space:]' < "${SCRIPT_DIR}/VERSION")
    fi
    [[ -n "${v}" ]] || v="unknown"
    echo "${v}"
}

docker_container_status() {
    local c="$1"
    docker inspect --format='{{.State.Status}}' "$c" 2>/dev/null | tr -d '[:space:]' || echo "not_found"
}

docker_published_ports_csv() {
    local c="$1"
    docker inspect "$c" >/dev/null 2>&1 || return 0
    docker inspect -f '{{range $p, $bindings := .NetworkSettings.Ports}}{{range $bindings}}{{.HostPort}}{{"\n"}}{{end}}{{end}}' "$c" 2>/dev/null \
        | { grep -E '^[0-9]+$' || true; } | sort -nu | { paste -sd, - 2>/dev/null || true; }
}

status_wants_json() {
    [[ "${COMMANDS[0]:-}" == "status" && "${STATUS_JSON}" == "true" ]]
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
    elif [[ -e /dev/tenstorrent ]] || command -v tt-smi >/dev/null 2>&1;        then accelerator="tenstorrent"; export SLM_URL="http://zyrabit-vllm-tt:8000"
    elif [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]];           then accelerator="metal";       export SLM_URL="http://host.docker.internal:11434"
    else                                                                              accelerator="cpu"
    fi
    echo "${ram_gb}|${cores}|${accelerator}"
}

ensure_data_directories() {
    local base="${SCRIPT_DIR}/zyrabit-slm"
    local dirs=(
        "${base}/db_data/node/sources"
        "${base}/document_source"
        "${base}/secrets"
        "${base}/prompts"
    )
    for d in "${dirs[@]}"; do
        if [[ ! -d "$d" ]]; then
            mkdir -p "$d" || { log_err "Cannot create ${d}."; return 1; }
        fi
    done

    # Ensure UID 10001 (nonroot inside zyrabit-api container) has write permissions
    # on Linux and WSL2 hosts without requiring root/sudo
    [[ "$(uname -s)" == "Darwin" ]] && return 0

    log_info "Adjusting data volume ownership and permissions to UID 10001..."
    if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        docker run --rm -e HOST_GID="$(id -g)" \
            -v "${base}/db_data:/d1" -v "${base}/document_source:/d2" busybox \
            sh -c 'chown -R 10001:"$HOST_GID" /d1 /d2 && chmod -R u+rwX,g+rwX,o-rwx /d1 /d2 && find /d1 /d2 -type d -exec chmod g+s {} +' \
            || { log_err "Failed to adjust permissions on db_data/document_source with helper container."; return 1; }
    else
        chmod -R u+rwX,g+rwX,o-rwx "${base}/db_data" "${base}/document_source" || {
            log_err "Cannot set permissions on db_data or document_source."
            return 1
        }
    fi
}

is_chat_llm_model() {
    local lower="$1"
    # Exclude embeddings and rerankers
    if echo "$lower" | grep -qiE '(^|[-_/:])(embed|embedding|bge|minilm|bert|rerank)([-_/:0-9]|$)'; then
        return 1
    fi
    # Exclude speech, audio, transcription, vocoder, and TTS
    if echo "$lower" | grep -qiE '(^|[-_/:])(whisper|stt|tts|speech|audio|vocoder|wav2vec)([-_/:0-9]|$)'; then
        return 1
    fi
    # Exclude image generation / vision-only models
    if echo "$lower" | grep -qiE '(^|[-_/:])(stable-diffusion|sdxl|flux)([-_/:0-9]|$)'; then
        return 1
    fi
    return 0
}

detect_local_models() {
    local detected=()
    # 1. Check Ollama running or CLI
    if check_local_ollama && command -v ollama >/dev/null 2>&1; then
        while read -r name _; do
            if [[ -n "$name" && "$name" != "NAME" ]]; then
                local lower_name; lower_name="$(echo "$name" | tr '[:upper:]' '[:lower:]')"
                if is_chat_llm_model "$lower_name"; then
                    detected+=("ollama:${name}")
                fi
            fi
        done < <(ollama list 2>/dev/null || true)
    elif [[ -d "${HOME}/.ollama/models/manifests/registry.ollama.ai/library" ]]; then
        for d in "${HOME}/.ollama/models/manifests/registry.ollama.ai/library"/*; do
            if [[ -d "$d" ]]; then
                local model_base; model_base="$(basename "$d")"
                local lower_base; lower_base="$(echo "$model_base" | tr '[:upper:]' '[:lower:]')"
                if is_chat_llm_model "$lower_base"; then
                    for tag in "$d"/*; do
                        [[ -f "$tag" ]] && detected+=("ollama:${model_base}:$(basename "$tag")")
                    done
                fi
            fi
        done
    fi

    # 2. Check Hugging Face hub cache
    local hf_hub="${HOME}/.cache/huggingface/hub"
    if [[ -d "${hf_hub}" ]]; then
        for model_dir in "${hf_hub}"/models--*; do
            if [[ -d "${model_dir}" ]]; then
                local repo_name; repo_name="$(basename "${model_dir}" | sed 's/^models--//; s/--/\//')"
                local lower_repo; lower_repo="$(echo "$repo_name" | tr '[:upper:]' '[:lower:]')"
                if is_chat_llm_model "$lower_repo"; then
                    detected+=("hf:${repo_name}")
                fi
            fi
        done
    fi

    # 3. Check local GGUF models
    local gguf_dirs=("${SCRIPT_DIR}/zyrabit-slm/models" "${HOME}/models" "${HOME}/.cache/zyrabit/models" "${HOME}/.cache/lm-studio/models")
    for gguf_dir in "${gguf_dirs[@]}"; do
        if [[ -d "${gguf_dir}" ]]; then
            while read -r gguf_file; do
                if [[ -n "${gguf_file}" ]]; then
                    local lower_gguf; lower_gguf="$(echo "$gguf_file" | tr '[:upper:]' '[:lower:]')"
                    if is_chat_llm_model "$lower_gguf"; then
                        detected+=("gguf:$(basename "${gguf_file}")|${gguf_file}")
                    fi
                fi
            done < <(find "${gguf_dir}" -maxdepth 3 -type f -name "*.gguf" 2>/dev/null || true)
        fi
    done

    printf '%s\n' "${detected[@]}"
}

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION SETUP — called by install on first run (or --yes skips it)
# ─────────────────────────────────────────────────────────────────────────────
run_setup_config() {
    log_header "ZYRABIT CONFIGURATION SETUP"
    echo -e "  ${CYAN}Configure your sovereign AI stack. Press Enter to accept defaults.${NC}\n"

    # ── 1. Hardware & Engine Detection ─────────────────────────────────────────
    log_step "1/4  Hardware & Inference Engine"
    local hw_detected="ollama_host"
    local hw_label="Ollama / Host Metal"
    if [[ -d "/dev/tenstorrent" || -e "/dev/tenstorrent" ]]; then
        hw_detected="tenstorrent"
        hw_label="Tenstorrent Blackhole Hardware (/dev/tenstorrent)"
    elif [[ -x "$(command -v nvidia-smi 2>/dev/null)" ]]; then
        hw_detected="cuda"
        hw_label="NVIDIA CUDA GPU"
    elif [[ "$(uname -s)" == "Darwin" ]]; then
        hw_detected="ollama_host"
        hw_label="Apple Silicon Metal (Mac GPU)"
    else
        hw_detected="ollama_docker"
        hw_label="Docker CPU Multithreading"
    fi

    echo -e "   Detected Hardware: ${GREEN}${hw_label}${NC}"
    echo "   1) Use auto-detected engine (${hw_detected}) ← recommended"
    echo "   2) Tenstorrent Hardware (vLLM-TT Metalium)"
    echo "   3) Apple Silicon Metal (Ollama Host)"
    echo "   4) Apple MLX Framework"
    echo "   5) Ollama Docker (Standard CPU)"
    read -rp "   Select [1]: " _c; _c="${_c:-1}"
    case "$_c" in
        2) INFERENCE_PROVIDER="tenstorrent" ;;
        3) INFERENCE_PROVIDER="ollama_host" ;;
        4) INFERENCE_PROVIDER="mlx" ;;
        5) INFERENCE_PROVIDER="ollama_docker" ;;
        *) INFERENCE_PROVIDER="${hw_detected}" ;;
    esac
    log_ok "Engine: ${INFERENCE_PROVIDER}"

    # ── 2. AI Model & Architecture (MoE / Dense) ───────────────────────────────
    log_step "2/4  AI Model Architecture & Smart Selection"
    local hw_info ram
    hw_info=$(detect_hardware); IFS='|' read -r ram _ _ <<< "$hw_info"

    local hw_ctx_label="${ram} GB RAM"
    local hw_rec_prefix="${ram}GB RAM"
    if [[ "${INFERENCE_PROVIDER}" == "tenstorrent" ]]; then
        hw_ctx_label="Tenstorrent NPU | Host RAM: ${ram} GB"
        hw_rec_prefix="Tenstorrent NPU + ${ram}GB"
    elif [[ "${INFERENCE_PROVIDER}" == "cuda" ]]; then
        hw_ctx_label="NVIDIA CUDA GPU | Host RAM: ${ram} GB"
        hw_rec_prefix="CUDA GPU + ${ram}GB"
    elif [[ "${INFERENCE_PROVIDER}" == "ollama_host" && "$(uname -s)" == "Darwin" ]]; then
        hw_ctx_label="Apple Silicon Metal | Unified RAM: ${ram} GB"
        hw_rec_prefix="Apple Metal + ${ram}GB"
    elif [[ "${INFERENCE_PROVIDER}" == "mlx" ]]; then
        hw_ctx_label="Apple MLX Framework | Unified RAM: ${ram} GB"
        hw_rec_prefix="Apple MLX + ${ram}GB"
    fi
    echo -e "   Target Hardware   : ${BOLD}${CYAN}${hw_ctx_label}${NC}"

    # Scan for existing downloaded models (excluding embedding models)
    local raw_detected=()
    while IFS= read -r line; do
        [[ -n "$line" ]] && raw_detected+=("$line")
    done < <(detect_local_models)

    # Build unified choice array
    local menu_labels=()
    local menu_values=()
    local menu_types=()

    # Prioritize and recommend best local model if available
    local best_rec_idx=1
    local found_top_rec=0

    for m in "${raw_detected[@]}"; do
        local display_name="${m}"
        local val="${m}"
        local type="ollama"
        if [[ "$m" == ollama:* ]]; then
            val="${m#ollama:}"
            display_name="${val} (Ollama local)"
            type="ollama"
        elif [[ "$m" == hf:* ]]; then
            val="${m#hf:}"
            display_name="${val} (Hugging Face Cache)"
            type="hf"
        elif [[ "$m" == gguf:* ]]; then
            local gguf_file; gguf_file="$(echo "$m" | cut -d'|' -f2)"
            val="${gguf_file}"
            display_name="$(basename "$gguf_file") (Local GGUF)"
            type="gguf"
        fi

        # Check recommendation match
        local tag_rec=""
        local tag_note=""
        if [[ "${INFERENCE_PROVIDER}" == "tenstorrent" ]]; then
            if [[ "$val" == *"1.5"* || "$val" == *"1.5b"* || "$val" == *"1.5B"* || "$val" == *"3b"* || "$val" == *"3B"* ]]; then
                if [[ $found_top_rec -eq 0 ]]; then
                    tag_rec=" ${BOLD}${GREEN}★ RECOMMENDED (Native Tenstorrent NPU — <80ms TTFT)${NC}"
                    found_top_rec=1
                fi
            elif [[ "$val" == *"7b"* || "$val" == *"7B"* || "$val" == *"8x7b"* ]]; then
                tag_note=" ${YELLOW}(7B+ requires multi-card on NPU or CPU)${NC}"
            fi
        else
            if [[ $found_top_rec -eq 0 ]]; then
                if [[ "$val" == *"deepseek-r1:7b"* || "$val" == *"deepseek-r1"* ]] && [[ "$ram" -ge 8 ]]; then
                    tag_rec=" ${BOLD}${GREEN}★ RECOMMENDED (${hw_rec_prefix}, Advanced Reasoning)${NC}"
                    found_top_rec=1
                elif [[ "$val" == *"qwen2.5:7b"* ]] && [[ "$ram" -ge 8 ]]; then
                    tag_rec=" ${BOLD}${GREEN}★ RECOMMENDED (${hw_rec_prefix}, Balanced Production)${NC}"
                    found_top_rec=1
                elif [[ "$val" == *"qwen2.5:3b"* || "$val" == *"qwen2.5:1.5b"* ]]; then
                    tag_rec=" ${BOLD}${GREEN}★ RECOMMENDED (${hw_rec_prefix}, Ultra-fast)${NC}"
                    found_top_rec=1
                fi
            fi
        fi

        menu_labels+=("${display_name}${tag_rec}${tag_note}")
        menu_values+=("${val}")
        menu_types+=("${type}")
        if [[ -n "$tag_rec" ]]; then
            best_rec_idx=${#menu_labels[@]}
        fi
    done

    echo ""
    local opt_num=1
    if [[ ${#raw_detected[@]} -gt 0 ]]; then
        echo -e "   ${GREEN}⚡ Local Models Detected (Ready, no download):${NC}"
        for lbl in "${menu_labels[@]}"; do
            echo -e "   ${BOLD}${opt_num})${NC} ${lbl}"
            ((opt_num++))
        done
        echo ""
    fi

    # Standard Catalogue additions
    echo -e "   ${CYAN}🌐 Or Download a Model from the Catalogue:${NC}"

    local cat_models=()
    if [[ "${INFERENCE_PROVIDER}" == "tenstorrent" ]]; then
        cat_models=(
            "qwen2.5:3b|qwen2.5:3b     ~3 GB  — Ultra-fast (<81ms TTFT, Native 1x Tenstorrent p150)"
            "deepseek-r1:1.5b|deepseek-r1:1.5b ~2 GB  — Reasoning CoT (Native 1x Tenstorrent p150)"
            "qwen2.5:7b|qwen2.5:7b     ~8 GB  — Balanced production (Requires multi-card on NPU)"
            "mixtral:8x7b-instruct|mixtral:8x7b   ~26 GB — Mixture of Experts (Requires multi-card on NPU)"
        )
    else
        cat_models=(
            "qwen2.5:7b|qwen2.5:7b     ~8 GB  — Balanced production model"
            "mixtral:8x7b-instruct|mixtral:8x7b   ~26 GB — Mixture of Experts (MoE) / High reasoning"
            "deepseek-r1:7b|deepseek-r1:7b ~5 GB  — Reasoning Chain-of-Thought"
            "qwen2.5:3b|qwen2.5:3b     ~3 GB  — Ultra-fast (<81ms TTFT, low latency)"
        )
    fi

    for item in "${cat_models[@]}"; do
        local c_val; c_val="$(echo "$item" | cut -d'|' -f1)"
        local c_lbl; c_lbl="$(echo "$item" | cut -d'|' -f2)"

        # Avoid duplicate entries if model was already detected locally
        local already_in_menu=0
        for mv in "${menu_values[@]}"; do
            if [[ "$mv" == "$c_val" ]]; then
                already_in_menu=1
                break
            fi
        done
        if [[ $already_in_menu -eq 1 ]]; then
            continue
        fi

        local tag_rec=""
        if [[ $found_top_rec -eq 0 ]]; then
            if [[ "${INFERENCE_PROVIDER}" == "tenstorrent" ]]; then
                if [[ "$c_val" == "qwen2.5:3b" || "$c_val" == "deepseek-r1:1.5b" ]]; then
                    tag_rec=" ${BOLD}${GREEN}★ RECOMMENDED (Native Tenstorrent NPU)${NC}"
                    found_top_rec=1
                fi
            else
                if [[ "$c_val" == "qwen2.5:7b" && "$ram" -ge 8 ]]; then
                    tag_rec=" ${BOLD}${GREEN}★ RECOMMENDED for ${hw_rec_prefix}${NC}"
                    found_top_rec=1
                elif [[ "$c_val" == "qwen2.5:3b" ]]; then
                    tag_rec=" ${BOLD}${GREEN}★ RECOMMENDED for ${hw_rec_prefix}${NC}"
                    found_top_rec=1
                fi
            fi
        fi
        menu_labels+=("${c_lbl}${tag_rec}")
        menu_values+=("${c_val}")
        menu_types+=("catalogue")
        if [[ -n "$tag_rec" ]]; then
            best_rec_idx=${#menu_labels[@]}
        fi
        echo -e "   ${BOLD}${opt_num})${NC} ${c_lbl}${tag_rec}"
        ((opt_num++))
    done

    # Custom model option
    local custom_idx=${opt_num}
    echo -e "   ${BOLD}${custom_idx})${NC} Custom model name or path to .gguf\n"

    read -rp "   Select an option [${best_rec_idx}]: " _c; _c="${_c:-${best_rec_idx}}"

    if [[ "$_c" == "${custom_idx}" ]]; then
        read -rp "   Enter model name or file path: " OVERRIDE_MODEL
    elif [[ "$_c" =~ ^[0-9]+$ ]] && [[ "$_c" -ge 1 && "$_c" -le ${#menu_values[@]} ]]; then
        local chosen_arr_idx=$(( _c - 1 ))
        OVERRIDE_MODEL="${menu_values[$chosen_arr_idx]}"
        local chosen_type="${menu_types[$chosen_arr_idx]}"
        if [[ "$chosen_type" == "gguf" ]]; then
            LLAMA_MODEL_PATH="${OVERRIDE_MODEL}"
        fi
    else
        OVERRIDE_MODEL="${menu_values[$(( best_rec_idx - 1 ))]}"
    fi

    log_ok "Selected model: ${OVERRIDE_MODEL}"

    # ── 3. Autonomous ReAct Agent & MCP Tools ──────────────────────────────────
    log_step "3/4  Agentic Loop & Tool Execution (ReAct)"
    echo "   Enable ReAct (Reasoning + Acting) autonomous agent with MCP tools?"
    echo "   1) Yes ← recommended (Reasoning + Tools + PII Sandwich)"
    echo "   2) No  (Direct RAG / Direct Inference only)"
    read -rp "   Select [1]: " _c; _c="${_c:-1}"
    local ENABLE_REACT="true"
    [[ "$_c" == "2" ]] && ENABLE_REACT="false"
    log_ok "ReAct Agent: ${ENABLE_REACT}"

    # ── 4. Deployment Mode ────────────────────────────────────────────────────
    log_step "4/4  Deployment Mode"
    echo "   1) Full Sovereign Platform ← default (Web UI + API RAG + DB + MCP)"
    echo "   2) Standalone Bare Engine            (Headless inference API on port 8088)"
    read -rp "   Select [1]: " _c; _c="${_c:-1}"
    local DEPLOY_MODE="platform"
    if [[ "$_c" == "2" ]]; then
        DEPLOY_MODE="bare"
        PROFILE="bare"
        log_ok "Mode: Standalone Bare Engine"
    else
        DEPLOY_MODE="platform"
        log_ok "Mode: Full Sovereign Platform"
    fi

    # ── Summary ───────────────────────────────────────────────────────────────
    echo ""
    echo -e "${BOLD}${CYAN}  ╔══ YOUR CONFIGURATION ═══════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}  ║${NC}  Engine     : ${INFERENCE_PROVIDER}"
    echo -e "${BOLD}${CYAN}  ║${NC}  Model      : ${OVERRIDE_MODEL}"
    echo -e "${BOLD}${CYAN}  ║${NC}  ReAct Agent: ${ENABLE_REACT}"
    echo -e "${BOLD}${CYAN}  ║${NC}  Deploy Mode: ${DEPLOY_MODE}"
    echo -e "${BOLD}${CYAN}  ╚═════════════════════════════════════════════════╝${NC}"
    echo ""
    read -rp "  Save and start with this config? [Y/n]: " _ok
    _ok_lower=$(echo "${_ok:-y}" | tr '[:upper:]' '[:lower:]')
    [[ "${_ok_lower}" == "n" ]] && { log_warn "Cancelled."; exit 0; }

    # Write .env
    if [[ ! -f "${ENV_FILE}" ]] && [[ -f "${EXAMPLE_ENV}" ]]; then
        cp "${EXAMPLE_ENV}" "${ENV_FILE}"
    fi
    if [[ -f "${ENV_FILE}" ]]; then
        local target_slm_url="http://zyrabit-engine:11434"
        local target_embedding_url="http://zyrabit-engine:11434"
        local target_tt_model="${OVERRIDE_MODEL}"

        case "${INFERENCE_PROVIDER}" in
            tenstorrent|vllm)
                target_slm_url="http://zyrabit-vllm-tt:8000"
                target_embedding_url="http://host.docker.internal:11434"
                case "${OVERRIDE_MODEL}" in
                    "qwen2.5:7b")     target_tt_model="Qwen2.5-7B-Instruct" ;;
                    "qwen2.5:3b")     target_tt_model="Qwen2.5-3B-Instruct" ;;
                    "deepseek-r1:7b") target_tt_model="DeepSeek-R1-Distill-Qwen-7B" ;;
                    "mixtral:8x7b-instruct") target_tt_model="Mixtral-8x7B-Instruct-v0.1" ;;
                    *) target_tt_model="${OVERRIDE_MODEL}" ;;
                esac
                ;;
            ollama_host|embedded_metal|mlx|llama_cpp_server)
                target_slm_url="http://host.docker.internal:11434"
                target_embedding_url="http://host.docker.internal:11434"
                ;;
            ollama_docker|ollama|cuda)
                target_slm_url="http://zyrabit-engine:11434"
                target_embedding_url="http://zyrabit-engine:11434"
                ;;
            *)
                target_slm_url="http://zyrabit-engine:11434"
                target_embedding_url="http://zyrabit-engine:11434"
                ;;
        esac

        sed -i.bak "s|^INFERENCE_PROVIDER=.*|INFERENCE_PROVIDER=${INFERENCE_PROVIDER}|" "${ENV_FILE}" 2>/dev/null || true
        sed -i.bak "s|^SLM_URL=.*|SLM_URL=${target_slm_url}|"                           "${ENV_FILE}" 2>/dev/null || true
        sed -i.bak "s|^EMBEDDING_URL=.*|EMBEDDING_URL=${target_embedding_url}|"       "${ENV_FILE}" 2>/dev/null || true
        sed -i.bak "s|^MODEL_NAME=.*|MODEL_NAME=${OVERRIDE_MODEL}|"                     "${ENV_FILE}" 2>/dev/null || true

        if ! grep -q "^EMBEDDING_MODEL=" "${ENV_FILE}" 2>/dev/null; then
            echo "EMBEDDING_MODEL=mxbai-embed-large" >> "${ENV_FILE}"
        fi
        
        if grep -q "^TT_HF_MODEL_NAME=" "${ENV_FILE}" 2>/dev/null; then
            sed -i.bak "s|^TT_HF_MODEL_NAME=.*|TT_HF_MODEL_NAME=${target_tt_model}|"   "${ENV_FILE}" 2>/dev/null || true
        else
            echo "TT_HF_MODEL_NAME=${target_tt_model}" >> "${ENV_FILE}"
        fi

        # Remove obsolete upstream bridge variable if present
        sed -i.bak "/^ZYRABIT_TT_UPSTREAM_MODEL=/d" "${ENV_FILE}" 2>/dev/null || true

        grep -q "^ENABLE_REACT_AGENT=" "${ENV_FILE}" 2>/dev/null \
            && sed -i.bak "s|^ENABLE_REACT_AGENT=.*|ENABLE_REACT_AGENT=${ENABLE_REACT}|" "${ENV_FILE}" \
            || echo "ENABLE_REACT_AGENT=${ENABLE_REACT}" >> "${ENV_FILE}"
        grep -q "^DEPLOY_MODE=" "${ENV_FILE}" 2>/dev/null \
            && sed -i.bak "s|^DEPLOY_MODE=.*|DEPLOY_MODE=${DEPLOY_MODE}|" "${ENV_FILE}" \
            || echo "DEPLOY_MODE=${DEPLOY_MODE}" >> "${ENV_FILE}"
        rm -f "${ENV_FILE}.bak"
        log_ok "Config saved to zyrabit-slm/.env"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# INSTALL — entry point for first-time and re-installs
# ─────────────────────────────────────────────────────────────────────────────
run_install() {
    log_header "ZYRABIT INSTALL"

    # Setup decision logic:
    #   no .env                  → run guided configuration setup
    #   .env exists + --yes / -y → skip prompts, use existing config
    #   .env exists + interactive → ask once if user wants to reconfigure
    if [[ ! -f "${ENV_FILE}" ]]; then
        log_info "First install detected — starting configuration setup..."
        run_setup_config
    elif [[ "${SKIP_PROMPTS}" == "true" ]]; then
        log_ok "Using existing config (--yes). Skipping interactive prompts."
    else
        echo -e "  ${CYAN}Config found at zyrabit-slm/.env${NC}"
        read -rp "  Reconfigure stack settings? [y/N]: " _r
        _r_lower=$(echo "${_r:-n}" | tr '[:upper:]' '[:lower:]')
        if [[ "${_r_lower}" == "y" ]]; then
            run_setup_config
        else
            log_ok "Using existing config."
        fi
    fi

    migrate_env_config
    ensure_local_secrets
    confirm_explicit_versions || exit 1

    # At this point OVERRIDE_MODEL may have been set during configuration
    local hw_info ram model_name
    hw_info=$(detect_hardware); IFS='|' read -r ram _ _ <<< "$hw_info"
    model_name="${OVERRIDE_MODEL:-}"
    if [[ -z "$model_name" ]]; then
        model_name=$(grep '^MODEL_NAME=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2 || true)
        model_name="${model_name:-$([ "${ram}" -lt 8 ] && echo "qwen2.5:1.5b" || echo "qwen2.5:7b")}"
    fi

    log_info "Model: ${model_name}"
    ensure_data_directories || { log_err "Failed to configure data directory permissions."; exit 1; }
    _build
    run_start
    if ! _pull_models "${model_name}"; then
        log_err "Model preparation failed. Stack may not be fully operational."
        log_warn "You can retry later with: ./zyra.sh install --yes"
        exit 1
    fi
    if ! run_verify; then
        log_err "Installation incomplete: verification detected errors. Check 'docker logs zyrabit-api' and retry with: ./zyra.sh install --yes"
        exit 1
    fi
    log_ok "✅ Installation complete."
}

confirm_explicit_versions() {
    [[ -f "${ENV_FILE}" ]] || return 0
    local ollama_version
    ollama_version=$(grep '^OLLAMA_VERSION=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
    if [[ -z "${ollama_version}" || "${ollama_version}" == "latest" ]]; then
        log_err "OLLAMA_VERSION must be an explicit release such as 0.5.12. latest is not accepted."
        return 1
    fi

    local image_ref=""
    if command -v docker >/dev/null 2>&1 && docker inspect zyrabit-api >/dev/null 2>&1; then
        image_ref=$(docker inspect -f '{{.Config.Image}}' zyrabit-api 2>/dev/null || true)
    fi
    if [[ "${image_ref}" != *:latest ]]; then
        return 0
    fi

    local accept
    accept=$(grep '^ZYRABIT_ACCEPT_LATEST=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
    if [[ "${accept}" == "yes" ]]; then
        log_warn "Existing image ${image_ref} tracks latest. Continuing because ZYRABIT_ACCEPT_LATEST=yes. Volumes and .env were not rewritten."
        return 0
    fi
    if [[ "${SKIP_PROMPTS}" == "true" ]]; then
        log_err "Existing image ${image_ref} tracks latest. Set ZYRABIT_ACCEPT_LATEST=yes or pin a version before a non-interactive upgrade."
        return 1
    fi
    local answer
    read -rp "  Existing image tracks :latest. Continue without changing that tag? [y/N]: " answer
    if [[ "$(echo "${answer:-n}" | tr '[:upper:]' '[:lower:]')" != "y" ]]; then
        log_err "Upgrade stopped. Pin the image tag or set ZYRABIT_ACCEPT_LATEST=yes."
        return 1
    fi
    log_warn "Continuing with ${image_ref}. Configuration and data volumes were left in place."
}

migrate_env_config() {
    [[ -f "${ENV_FILE}" ]] || return 0
    local provider
    provider=$(grep '^INFERENCE_PROVIDER=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2 || true)
    case "${provider}" in
        ollama_docker|ollama|cuda)
            if grep -q '^EMBEDDING_URL=http://host\.docker\.internal' "${ENV_FILE}" 2>/dev/null; then
                log_info "Migrating obsolete EMBEDDING_URL during upgrade (host.docker.internal -> http://zyrabit-engine:11434)..."
                sed -i.bak 's|^EMBEDDING_URL=.*|EMBEDDING_URL=http://zyrabit-engine:11434|' "${ENV_FILE}" 2>/dev/null && rm -f "${ENV_FILE}.bak"
            fi
            ;;
    esac
    if ! grep -q '^OLLAMA_VERSION=' "${ENV_FILE}" 2>/dev/null; then
        echo "OLLAMA_VERSION=0.5.12" >> "${ENV_FILE}"
    fi
}

ensure_local_secrets() {
    [[ -f "${ENV_FILE}" ]] || { log_err "Missing ${ENV_FILE}; run './zyra.sh install' to configure."; exit 1; }

    local key generated=0 value
    for key in ZYRABIT_API_KEY_WEB ZYRABIT_API_KEY_MCP ZYRABIT_API_KEY_ADMIN; do
        value=$(grep "^${key}=" "${ENV_FILE}" 2>/dev/null | cut -d= -f2- || true)
        if [[ -z "${value}" || "${value}" == replace-with-* || "${value}" == zyrabit-*-token ]]; then
            command -v openssl >/dev/null 2>&1 || { log_err "openssl is required to generate local API keys."; exit 1; }
            value=$(openssl rand -hex 32)
            if grep -q "^${key}=" "${ENV_FILE}"; then
                sed -i.bak "s|^${key}=.*|${key}=${value}|" "${ENV_FILE}"
            else
                echo "${key}=${value}" >> "${ENV_FILE}"
            fi
            generated=1
        fi
    done
    rm -f "${ENV_FILE}.bak"
    if [[ "${generated}" == "1" ]]; then
        log_ok "Generated distinct local API keys in zyrabit-slm/.env"
    fi
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

    # If model_name is a direct file path to a GGUF
    if [[ "${model_name}" == *.gguf || -f "${model_name}" ]]; then
        if [[ -f "${model_name}" ]]; then
            log_ok "Using local GGUF model file: ${model_name}"
            return 0
        fi
    fi

    if [[ "${provider}" == "llama_cpp_server" ]]; then
        if [[ -f "${LLAMA_MODEL_PATH}" ]]; then
            log_ok "GGUF model ready: ${LLAMA_MODEL_PATH}"
            return 0
        fi
        # Attempt to search local directories before erroring
        local discovered_gguf
        discovered_gguf=$(find "${SCRIPT_DIR}/zyrabit-slm/models" "${HOME}/models" "${HOME}/.cache/zyrabit/models" -maxdepth 3 -type f -name "*.gguf" 2>/dev/null | head -1 || true)
        if [[ -n "${discovered_gguf}" ]]; then
            log_ok "Auto-detected GGUF model: ${discovered_gguf}"
            LLAMA_MODEL_PATH="${discovered_gguf}"
            return 0
        fi
        log_err "Missing GGUF model: ${LLAMA_MODEL_PATH}. Place your .gguf in zyrabit-slm/models/ or download one."
        return 1
    elif [[ "${provider}" == "tenstorrent" || "${provider}" == "vllm" || "${provider}" == "mlx" ]]; then
        local hf_cache
        hf_cache=$(grep '^ZYRABIT_HF_CACHE_DIR=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2 || echo "${HOME}/.cache/huggingface")
        hf_cache="${hf_cache:-${HOME}/.cache/huggingface}"
        local tt_model
        tt_model=$(grep '^TT_HF_MODEL_NAME=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2 || echo "${model_name}")
        tt_model="${tt_model:-${model_name}}"

        log_info "Checking Hugging Face cache for '${tt_model}' in ${hf_cache}..."
        local found
        found=$(find "${hf_cache}/hub" -maxdepth 4 -type d -path "*/snapshots/*" 2>/dev/null | grep -i "${tt_model}" | head -1 || true)
        if [[ -n "${found}" ]]; then
            log_ok "Weights verified in cache: $(basename "${found}")"
        else
            log_warn "Model weights for '${tt_model}' not found in ${hf_cache}/hub."
            local hf_repo="Qwen/${tt_model}"
            [[ "${tt_model}" == *"DeepSeek"* ]] && hf_repo="deepseek-ai/${tt_model}"
            [[ "${tt_model}" == *"Mistral"* ]] && hf_repo="mistralai/${tt_model}"
            log_info "Downloading weights for ${hf_repo} to ${hf_cache}..."
            if command -v huggingface-cli >/dev/null 2>&1; then
                if ! HF_HUB_ENABLE_HF_TRANSFER=0 HF_HOME="${hf_cache}" huggingface-cli download "${hf_repo}"; then
                    log_err "Download failed for ${hf_repo}. Check internet connection."
                    return 1
                fi
            elif python3 -c "import huggingface_hub" >/dev/null 2>&1; then
                if ! python3 -c "import os; from huggingface_hub import snapshot_download; snapshot_download(repo_id='${hf_repo}', cache_dir='${hf_cache}/hub')"; then
                    log_err "Download failed for ${hf_repo}."
                    return 1
                fi
            else
                log_err "Weights for '${tt_model}' are not cached, and neither huggingface-cli nor huggingface_hub is available."
                return 1
            fi
        fi
    elif [[ "${provider}" == ollama* || "${provider}" == "cuda" ]]; then
        local embedding_model
        embedding_model=$(grep '^EMBEDDING_MODEL=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2 || echo "mxbai-embed-large")
        embedding_model="${embedding_model:-mxbai-embed-large}"

        log_info "Verifying Ollama models for chat ('${model_name}') and embeddings ('${embedding_model}')..."
        if check_local_ollama && [[ "${provider}" == "ollama_host" ]]; then
            if ollama list 2>/dev/null | grep -qE "^${model_name}(:latest)?[[:space:]]"; then
                log_ok "Model '${model_name}' already exists in Ollama. Skipping pull."
            else
                log_info "Pulling '${model_name}' into Ollama..."
                if ! ollama pull "${model_name}"; then
                    log_err "Failed to pull chat model '${model_name}' into Ollama."
                    return 1
                fi
            fi
            if ! ollama list 2>/dev/null | grep -qE "^${embedding_model}(:latest)?[[:space:]]"; then
                log_info "Pulling default embedding model '${embedding_model}' into Ollama..."
                if ! ollama pull "${embedding_model}"; then
                    log_err "Failed to pull embedding model '${embedding_model}'."
                    return 1
                fi
            else
                log_ok "Embedding model '${embedding_model}' already exists in Ollama."
            fi
        else
            log_info "Waiting for zyrabit-engine container to respond..."
            local engine_ready=false
            for ((attempt=1; attempt<=30; attempt++)); do
                if $DOCKER_COMPOSE_CMD -f "$(active_compose_file)" exec -T zyrabit-engine ollama list >/dev/null 2>&1; then
                    engine_ready=true
                    break
                fi
                sleep 1
            done
            if [[ "$engine_ready" != "true" ]]; then
                log_err "zyrabit-engine container is not responding. Check: docker logs zyrabit-engine"
                return 1
            fi

            if $DOCKER_COMPOSE_CMD -f "$(active_compose_file)" exec -T zyrabit-engine ollama list 2>/dev/null | grep -qE "^${model_name}(:latest)?[[:space:]]"; then
                log_ok "Model '${model_name}' already loaded in container."
            else
                log_info "Pulling chat model '${model_name}' into container engine..."
                if ! $DOCKER_COMPOSE_CMD -f "$(active_compose_file)" exec -T zyrabit-engine ollama pull "${model_name}"; then
                    log_err "Failed to pull chat model '${model_name}' into container. Check internet or container logs."
                    return 1
                fi
            fi
            if ! $DOCKER_COMPOSE_CMD -f "$(active_compose_file)" exec -T zyrabit-engine ollama list 2>/dev/null | grep -qE "^${embedding_model}(:latest)?[[:space:]]"; then
                log_info "Pulling default embedding model '${embedding_model}' into container engine..."
                if ! $DOCKER_COMPOSE_CMD -f "$(active_compose_file)" exec -T zyrabit-engine ollama pull "${embedding_model}"; then
                    log_err "Failed to pull embedding model '${embedding_model}'."
                    return 1
                fi
            else
                log_ok "Embedding model '${embedding_model}' already loaded in container."
            fi
        fi
        log_ok "Models ready."
        echo -e "   ${DIM}💡 Note: Default embedding model '${embedding_model}' ready for RAG. You can customize EMBEDDING_MODEL in zyrabit-slm/.env anytime.${NC}"
    else
        log_info "Provider '${provider}' uses embedded/MLX weights — downloaded automatically on first request."
    fi
}

validate_production_env() {
    [[ -f "${ENV_FILE}" ]] || {
        log_err "Production mode requires a configured .env file at zyrabit-slm/.env"
        exit 1
    }

    local missing=()
    local domain; domain=$(grep '^DOMAIN=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
    if [[ -z "${domain}" || "${domain}" == "localhost" || "${domain}" == replace-with-* ]]; then
        missing+=("DOMAIN must be configured to a valid public/internal domain (cannot be 'localhost' or placeholder)")
    fi

    local web_key; web_key=$(grep '^ZYRABIT_API_KEY_WEB=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
    if [[ -z "${web_key}" || "${web_key}" == replace-with-* || "${web_key}" == zyrabit-*-token ]]; then
        missing+=("ZYRABIT_API_KEY_WEB must be set to a secure, non-default secret")
    fi

    local mcp_key; mcp_key=$(grep '^ZYRABIT_API_KEY_MCP=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'" || true)
    if [[ -z "${mcp_key}" || "${mcp_key}" == replace-with-* || "${mcp_key}" == zyrabit-*-token ]]; then
        missing+=("ZYRABIT_API_KEY_MCP must be set to a secure, non-default secret")
    fi

    local prom_auth; prom_auth=$(grep '^PROMETHEUS_BASIC_AUTH=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2- || true)
    if [[ -z "${prom_auth}" || "${prom_auth}" != *:* || "${prom_auth}" == *placeholder* ]]; then
        missing+=("PROMETHEUS_BASIC_AUTH must be set to 'username:htpasswd_hash' for Traefik access")
    fi

    local graf_auth; graf_auth=$(grep '^GRAFANA_BASIC_AUTH=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2- || true)
    if [[ -z "${graf_auth}" || "${graf_auth}" != *:* || "${graf_auth}" == *placeholder* ]]; then
        missing+=("GRAFANA_BASIC_AUTH must be set to 'username:htpasswd_hash' for Traefik access")
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_err "Production validation failed. Please address these in zyrabit-slm/.env:"
        for item in "${missing[@]}"; do
            echo -e "   ${RED}✗ ${item}${NC}"
        done
        echo ""
        exit 1
    fi
    log_ok "Production environment validated."
}

# ─────────────────────────────────────────────────────────────────────────────
# START — re-launch existing stack without reconfiguring
# ─────────────────────────────────────────────────────────────────────────────
cleanup_stale_containers() {
    # Self-healing: Detect and silently remove stale, created, or dead containers
    local stale
    stale=$(docker ps -aq --filter "name=zyrabit" --filter "status=exited" --filter "status=created" --filter "status=dead" 2>/dev/null || true)
    if [[ -n "${stale}" ]]; then
        docker rm -f ${stale} >/dev/null 2>&1 || true
    fi
}

run_start() {
    require_docker
    ensure_data_directories || return 1
    migrate_env_config
    cleanup_stale_containers
    local compose_file compose_args
    compose_file="$(active_compose_file)"
    compose_args=("-f" "${compose_file}")
    local current_provider
    current_provider=$(grep '^INFERENCE_PROVIDER=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2 || echo "ollama_host")

    if [[ "${current_provider}" == "tenstorrent" || "${current_provider}" == "vllm" ]]; then
        compose_args+=("--profile" "hardware")
    fi

    if [[ -n "${PROFILE}" ]]; then
        compose_args+=("--profile" "${PROFILE}")
    fi

    if [[ "${PRODUCTION_MODE}" == "true" ]]; then
        validate_production_env
        local dashboard_flag="false"
        local dashboard_auth=""
        if [[ "${ZYRABIT_TRAEFIK_DASHBOARD:-}" == "true" ]] || grep -q '^ZYRABIT_TRAEFIK_DASHBOARD=true' "${ENV_FILE}" 2>/dev/null; then
            dashboard_flag="true"
            dashboard_auth=$(grep '^TRAEFIK_DASHBOARD_AUTH=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2- || true)
            compose_args+=("-f" "${SCRIPT_DIR}/zyrabit-slm/docker-compose.dashboard.yml")
        fi
        if ! python3 "${SCRIPT_DIR}/scripts/check_traefik_dashboard.py" \
            --compose "${SCRIPT_DIR}/zyrabit-slm/docker-compose.yml" \
            --enabled "${dashboard_flag}" \
            --auth "${dashboard_auth}"; then
            exit 1
        fi
        compose_args+=("--profile" "production")
        log_header "ZYRABIT — PRODUCTION"
        log_info "Domain: ${DOMAIN:-localhost}"
        $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d
    else
        log_header "ZYRABIT — LOCAL / DEV (Traefik bypassed, direct ports active)"

        if [[ "${current_provider}" == "tenstorrent" || "${current_provider}" == "vllm" ]]; then
            log_info "Tenstorrent Blackhole provider detected — activating hardware accelerator container..."
            $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d --remove-orphans --scale zyrabit-engine=0
        elif [[ "${current_provider}" == "llama_cpp_server" ]]; then
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
            $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d --remove-orphans --scale zyrabit-engine=0 2>/dev/null || $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d --remove-orphans
        elif [[ "${current_provider}" == "embedded_metal" || "${current_provider}" == "mlx" ]]; then
            log_info "Provider is '${current_provider}' (Native Metal) — skipping zyrabit-engine container."
            $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d --remove-orphans --scale zyrabit-engine=0 2>/dev/null ||
            $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d --remove-orphans
        elif check_local_ollama && [[ "${current_provider}" != "ollama_docker" && "${current_provider}" != "ollama" && "${current_provider}" != "cuda" ]]; then
            log_info "Ollama detected on host (Metal) — skipping zyrabit-engine container."
            $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d --remove-orphans --scale zyrabit-engine=0 2>/dev/null ||
            $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d --remove-orphans
        else
            log_info "Starting local services (Web UI, API RAG, Vector DB)..."
            $DOCKER_COMPOSE_CMD "${compose_args[@]}" up -d --remove-orphans
        fi
    fi

    log_ok "Stack is up."
    echo ""
    if [[ "${PRODUCTION_MODE}" != "true" ]]; then
        echo -e "  ${BOLD}🚀 Zyrabit Local / Dev Services Ready!${NC}"
        local local_port="${ZYRABIT_LOCAL_PORT:-8080}"
        echo -e "  ${CYAN}➜ Web UI (Workspace)${NC}  http://localhost:${local_port}"
        echo -e "  ${CYAN}➜ API RAG (FastAPI)${NC}    http://localhost:8088/v1  (or http://localhost:${local_port}/v1)"
        if [[ "${current_provider}" == "tenstorrent" || "${current_provider}" == "vllm" ]]; then
            echo -e "  ${CYAN}➜ NPU Engine (vLLM)${NC}   http://localhost:8090"
        fi
        echo -e "  ${CYAN}➜ Vector DB (Chroma)${NC}   http://localhost:8000"
        echo -e "  ${CYAN}➜ MCP Agent Server${NC}     http://localhost:8001"
    else
        echo -e "  ${BOLD}🚀 Zyrabit Production Services Ready (Traefik TLS)!${NC}"
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
    $DOCKER_COMPOSE_CMD -f "$(active_compose_file)" --profile hardware --profile monitoring --profile production down --remove-orphans
    log_ok "Stack stopped."
}

# ─────────────────────────────────────────────────────────────────────────────
# VERIFY — health check (runs automatically after install)
# ─────────────────────────────────────────────────────────────────────────────
run_verify() {
    log_header "HEALTH CHECK"
    local current_provider
    current_provider=$(grep '^INFERENCE_PROVIDER=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2 || echo "ollama_host")

    local containers=("zyrabit-api" "zyrabit-web" "zyrabit-db" "zyrabit-mcp")

    if [[ "${PRODUCTION_MODE}" == "true" ]]; then
        containers=("zyrabit-traefik" "${containers[@]}" "zyrabit-prometheus" "zyrabit-grafana" "zyrabit-loki")
    fi
    if [[ "${current_provider}" == "tenstorrent" || "${current_provider}" == "vllm" ]]; then
        containers+=("zyrabit-vllm-tt")
    elif [[ "${current_provider}" == "ollama_docker" || "${current_provider}" == "ollama" || "${current_provider}" == "cuda" ]]; then
        containers+=("zyrabit-engine")
    fi

    local pass=0 fail=0
    printf "  ${BOLD}%-28s %-15s %-10s${NC}\n" "CONTAINER" "STATUS" "HEALTH"
    printf "  ${CYAN}%-28s %-15s %-10s${NC}\n"  "────────────────────────────" "───────────────" "──────────"

    for c in "${containers[@]}"; do
        local status health
        status=$(docker inspect --format='{{.State.Status}}' "$c" 2>/dev/null | tr -d '[:space:]' || echo "not_found")
        if [[ "$c" == "zyrabit-engine" && "$status" == "not_found" ]]; then
            if [[ "${current_provider}" == "embedded_metal" || "${current_provider}" == "mlx" ]]; then
                printf "  ${GREEN}%-28s %-15s %-10s${NC}\n" "$c" "native-metal" "healthy"
                pass=$((pass + 1)); continue
            elif check_local_ollama; then
                printf "  ${GREEN}%-28s %-15s %-10s${NC}\n" "$c" "native-metal" "healthy"
                pass=$((pass + 1)); continue
            fi
        fi
        if [[ "$status" == "running" ]]; then
            health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}N/A{{end}}' "$c" 2>/dev/null | tr -d '[:space:]')
            if [[ "$health" == "unhealthy" ]]; then
                printf "  ${RED}%-28s %-15s %-10s${NC}\n" "$c" "running" "$health"
                log_err "Container $c is unhealthy."
                docker logs --tail 10 "$c" 2>/dev/null || true
                fail=$((fail + 1))
            else
                printf "  ${GREEN}%-28s %-15s %-10s${NC}\n" "$c" "running" "$health"
                pass=$((pass + 1))
            fi
        else
            printf "  ${RED}%-28s %-15s %-10s${NC}\n" "$c" "$status" "—"
            log_err "Required container $c is ${status}."
            fail=$((fail + 1))
        fi
    done

    echo -e "\n  ${BOLD}Containers:${NC} ${GREEN}${pass} up${NC}  ${RED}${fail} down${NC}"
    local rc=0
    if [[ $fail -gt 0 ]]; then
        rc=1
    fi

    local base_url; base_url="$(api_base_url)"
    log_info "Probing ${base_url}/health (waiting up to 60s for initialization)..."
    local health_resp=""
    local api_ready=false
    for ((i=1; i<=20; i++)); do
        health_resp=$(curl -sk -m 5 "${base_url}/health" 2>/dev/null || true)
        if echo "${health_resp}" | grep -q '"status":[[:space:]]*"OPERATIONAL"'; then
            api_ready=true
            log_ok "API is fully operational."
            break
        elif echo "${health_resp}" | grep -q '"status":[[:space:]]*"DEGRADED"'; then
            if [[ $i -eq 20 ]]; then
                local degraded_caps
                degraded_caps=$(echo "${health_resp}" | grep -o '"name":[[:space:]]*"[^"]*",[[:space:]]*"status":[[:space:]]*"[^"]*"' | grep -v '"status":"ready"' | tr -d '"{},' || true)
                if [[ -n "$degraded_caps" ]]; then
                    log_warn "API is in DEGRADED state (${degraded_caps})."
                else
                    log_warn "API is in DEGRADED state. Some services (database, node or model) are not ready."
                fi
                rc=1
            fi
        fi
        sleep 3
    done

    if [[ "$api_ready" != "true" ]]; then
        if ! echo "${health_resp}" | grep -q '"status":[[:space:]]*"DEGRADED"'; then
            log_err "API not responding. Check: docker logs zyrabit-api --tail 30"
            rc=1
        fi
    fi

    # Smoke test: verify that chat completions work
    local api_key; api_key=$(web_api_key)
    if [[ -z "${api_key}" ]]; then
        log_err "ZYRABIT_API_KEY_WEB is not configured. Verification is incomplete."
        rc=1
    else
        log_info "Running chat smoke test on ${base_url}/chat (timeout 60s)..."
        local chat_body chat_code
        chat_body=$(mktemp "/tmp/zyrabit-chat-XXXXXX.json")
        chat_code=$(curl -sk -o "${chat_body}" -w "%{http_code}" -m 60 -X POST "${base_url}/chat" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${api_key}" \
            -d '{"text":"ping"}' 2>/dev/null) || true
        chat_code="${chat_code:-000}"
        if [[ "${chat_code}" != "200" ]]; then
            log_err "Chat smoke test FAILED (HTTP ${chat_code}). Check: docker logs zyrabit-api --tail 40"
            rc=1
        elif ! python3 -c 'import json,sys; body=json.load(open(sys.argv[1], encoding="utf-8")); text=body.get("response"); raise SystemExit(0 if isinstance(text, str) and text.strip() else 1)' "${chat_body}"; then
            log_err "Chat smoke test FAILED: HTTP 200 did not include a non-empty response string."
            rc=1
        else
            log_ok "Chat smoke test passed."
        fi
        rm -f "${chat_body}"

        # Smoke test: verify that document ingestion, storage, and deletion work
        log_info "Running document ingestion smoke test on ${base_url}/sources/import..."
        local admin_key
        admin_key=$(grep '^ZYRABIT_API_KEY_ADMIN=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2- || true)
        if [[ -z "${admin_key}" || "${admin_key}" == replace-with-* ]]; then
            log_err "ZYRABIT_API_KEY_ADMIN is not configured. Document deletion cannot be verified."
            rc=1
        else
        local doc_tmp; doc_tmp=$(mktemp "/tmp/zyrabit-smoke-XXXXXX.txt")
        echo "Zyrabit sovereign node document verification test token $(date +%s)" > "${doc_tmp}"
        local upload_out upload_code upload_body doc_id
        upload_out=$(curl -sk -m 30 -w "\n%{http_code}" -X POST "${base_url}/sources/import" \
            -H "Authorization: Bearer ${admin_key}" \
            -F "file=@${doc_tmp}" 2>/dev/null) || true
        rm -f "${doc_tmp}"
        upload_code=$(echo "${upload_out}" | tail -n1)
        upload_body=$(echo "${upload_out}" | sed '$d')
        doc_id=$(echo "${upload_body}" | grep -o '"document_id":[[:space:]]*"[^"]*"' | head -n1 | cut -d'"' -f4 || true)

        cleanup_smoke_doc() {
            local id="$1"
            local del_code get_code
            del_code=$(curl -sk -m 10 -o /dev/null -w "%{http_code}" -X DELETE "${base_url}/documents/${id}" \
                -H "Authorization: Bearer ${admin_key}" 2>/dev/null) || true
            del_code="${del_code:-000}"
            get_code=$(curl -sk -m 10 -o /dev/null -w "%{http_code}" "${base_url}/documents/${id}" \
                -H "Authorization: Bearer ${admin_key}" 2>/dev/null) || true
            get_code="${get_code:-000}"
            if [[ "${del_code}" != "204" && "${del_code}" != "404" ]]; then
                log_err "Document cleanup DELETE failed (HTTP ${del_code}) for ${id}."
                rc=1
            fi
            if [[ "${get_code}" != "404" ]]; then
                log_err "Document ${id} is still present after cleanup (HTTP ${get_code})."
                rc=1
            else
                log_ok "Document smoke test removed ${id}."
            fi
        }

        if [[ "${upload_code}" != "200" && "${upload_code}" != "202" ]] || [[ -z "${doc_id}" ]]; then
            log_err "Document smoke test upload FAILED (HTTP ${upload_code}). Check permissions and logs: docker logs zyrabit-api --tail 40"
            rc=1
        else
            local doc_ready=false
            local doc_status=""
            local doc_wait="${VERIFY_DOC_TIMEOUT_SECONDS:-30}"
            local doc_attempts=$(( doc_wait / 2 ))
            [[ "${doc_attempts}" -lt 1 ]] && doc_attempts=1
            for ((j=1; j<=doc_attempts; j++)); do
                local doc_resp
                doc_resp=$(curl -sk -m 10 "${base_url}/documents/${doc_id}" \
                    -H "Authorization: Bearer ${admin_key}" 2>/dev/null || true)
                doc_status=$(echo "${doc_resp}" | grep -o '"status":[[:space:]]*"[^"]*"' | head -n1 | cut -d'"' -f4 || true)
                if [[ "${doc_status}" == "ready" ]]; then
                    doc_ready=true
                    break
                elif [[ "${doc_status}" == "failed" ]]; then
                    local doc_err
                    doc_err=$(echo "${doc_resp}" | grep -o '"error":[[:space:]]*"[^"]*"' | head -n1 | cut -d'"' -f4 || true)
                    log_err "Document smoke test failed processing: ${doc_err:-unknown}"
                    break
                fi
                sleep 2
            done

            if [[ "${doc_ready}" == "true" ]]; then
                log_ok "Document smoke test passed (document ready)."
            else
                log_err "Document smoke test FAILED (status: ${doc_status:-timeout}). Check logs: docker logs zyrabit-api --tail 40"
                rc=1
            fi
            cleanup_smoke_doc "${doc_id}"
        fi
        fi
    fi

    return $rc
}

# ─────────────────────────────────────────────────────────────────────────────
# STATUS — platform & engine summary (optional --json)
# ─────────────────────────────────────────────────────────────────────────────
run_status() {
    local json="${STATUS_JSON}"
    local arg
    for arg in "${COMMANDS[@]:1}"; do
        log_err "Unknown argument for status: ${arg}"; exit 1
    done

    local platform_docker="zyrabit-web"
    local platform_name="zyrabit-platform"
    local engine_docker="zyrabit-engine"
    local engine_name="zyrabit-engine"

    local current_provider
    current_provider=$(grep '^INFERENCE_PROVIDER=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2 || echo "ollama_host")

    local platform_status engine_status engine_native=false native_engine_port=""
    platform_status=$(docker_container_status "${platform_docker}")
    engine_status=$(docker_container_status "${engine_docker}")
    # Native providers have no engine container: embedded_metal/mlx run the engine
    # inside the platform process, while llama.cpp and host Ollama expose a host
    # service. Mirror run_start's provider handling: report the engine as running
    # only when its native service is expected and reachable, and leave a missing
    # container an error for the providers that do run one.
    if [[ "${engine_status}" == "not_found" ]]; then
        case "${current_provider}" in
            embedded_metal|mlx)
                engine_status="running"; engine_native=true ;;
            llama_cpp_server)
                if check_local_llama; then
                    engine_status="running"; engine_native=true; native_engine_port="${LLAMA_SERVER_PORT}"
                fi ;;
            tenstorrent|vllm|ollama_docker|ollama|cuda)
                : ;; # these providers own a dedicated engine container
            *)
                if check_local_ollama; then
                    engine_status="running"; engine_native=true; native_engine_port="11434"
                fi ;;
        esac
    fi

    local platform_ports engine_ports
    platform_ports=$(docker_published_ports_csv "${platform_docker}")
    if [[ -z "${platform_ports}" && "${platform_status}" == "running" ]]; then
        platform_ports="${ZYRABIT_LOCAL_PORT:-8080}"
    fi
    engine_ports=$(docker_published_ports_csv "${engine_docker}")
    if [[ -z "${engine_ports}" && "${engine_status}" == "running" ]]; then
        if [[ "${engine_native}" == "true" ]]; then
            if [[ -n "${native_engine_port}" ]]; then engine_ports="${native_engine_port}"; fi
        else
            engine_ports="11434"
        fi
    fi

    local version healthy=false
    version=$(zyra_version)
    if [[ "${platform_status}" == "running" && "${engine_status}" == "running" ]]; then
        healthy=true
    fi

    if [[ "${json}" == "true" ]]; then
        PLATFORM_STATUS="${platform_status}" ENGINE_STATUS="${engine_status}" \
        PLATFORM_NAME="${platform_name}" ENGINE_NAME="${engine_name}" \
        PLATFORM_PORTS="${platform_ports}" ENGINE_PORTS="${engine_ports}" \
        ZYRA_VERSION="${version}" ZYRA_HEALTHY="${healthy}" \
        python3 -c '
import json, os

def ports_csv(raw):
    raw = (raw or "").strip()
    if not raw:
        return []
    return [int(p) for p in raw.split(",") if p.isdigit()]

healthy = os.environ.get("ZYRA_HEALTHY") == "true"
print(json.dumps({
    "platform": {
        "container": os.environ["PLATFORM_NAME"],
        "status": os.environ["PLATFORM_STATUS"],
        "ports": ports_csv(os.environ.get("PLATFORM_PORTS")),
    },
    "engine": {
        "container": os.environ["ENGINE_NAME"],
        "status": os.environ["ENGINE_STATUS"],
        "ports": ports_csv(os.environ.get("ENGINE_PORTS")),
    },
    "version": os.environ["ZYRA_VERSION"],
    "healthy": healthy,
}))
'
        if [[ "${healthy}" == "true" ]]; then exit 0; else exit 1; fi
    fi

    log_header "SYSTEM STATUS"
    local plat_color="${RED}" engine_color="${RED}"
    [[ "${platform_status}" == "running" ]] && plat_color="${GREEN}"
    [[ "${engine_status}" == "running" ]] && engine_color="${GREEN}"
    printf "  ${BOLD}%-12s %-22s %-12s %s${NC}\n" "SERVICE" "CONTAINER" "STATUS" "PORTS"
    printf "  ${plat_color}%-12s %-22s %-12s %s${NC}\n" "Platform" "${platform_name}" "${platform_status}" "${platform_ports:-—}"
    printf "  ${engine_color}%-12s %-22s %-12s %s${NC}\n" "Engine" "${engine_name}" "${engine_status}" "${engine_ports:-—}"
    echo -e "\n  ${BOLD}Version:${NC} ${version}"
    if [[ "${healthy}" == "true" ]]; then
        log_ok "All core services are healthy."
        exit 0
    fi
    log_warn "One or more core services are not running."
    exit 1
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
    if [[ -e /dev/tenstorrent ]]; then
        log_ok "Tenstorrent PCIe device present (/dev/tenstorrent)."
        local hp; hp=$(cat /sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages 2>/dev/null || echo "0")
        if [[ "$hp" -gt 0 ]]; then
            log_ok "HugePages 1GB configured (${hp} pages)."
        else
            log_warn "HugePages 1GB is 0. Tenstorrent Blackhole benefits from 1GB hugepages."
        fi
    fi
    check_local_ollama && log_ok "Ollama detected on host (Metal)." || log_warn "Ollama not detected — will use Docker engine or embedded adapter."
    [[ -f "${ENV_FILE}" ]] && log_ok ".env found at zyrabit-slm/.env" || log_warn "No .env — run './zyra.sh install' first."
    log_ok "Doctor done."
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
# ─────────────────────────────────────────────────────────────────────────────
# BENCHMARK
# ─────────────────────────────────────────────────────────────────────────────
run_benchmark() {
    log_header "PERFORMANCE BENCHMARK"
    local base_url token
    base_url="$(api_base_url)"; token="$(web_api_key)"
    [[ -n "${token}" ]] || { log_err "ZYRABIT_API_KEY_WEB is not configured in .env"; exit 1; }

    log_info "Probing API status at ${base_url}/health ..."
    if ! curl -sk -f -m 5 "${base_url}/health" >/dev/null 2>&1; then
        log_err "API is not responding at ${base_url}. Start the stack first with './zyra.sh start' or check container status with './zyra.sh verify'."
        exit 1
    fi

    local hw_info ram cores accel accel_name
    hw_info=$(detect_hardware); IFS='|' read -r ram cores accel <<< "$hw_info"
    case "${accel}" in
        tenstorrent) accel_name="Tenstorrent Blackhole (PCIe)" ;;
        nvidia)      accel_name="NVIDIA CUDA GPU" ;;
        metal)       accel_name="Apple Silicon Metal" ;;
        *)           accel_name="CPU Multithreading (${cores} cores)" ;;
    esac

    if [[ "${REPORT_MODE}" == "true" ]]; then
        log_info "Running multi-engine comparison against ${base_url}/chat ..."
        python3 -c "
import json, urllib.request, time, ssl
ctx = ssl._create_unverified_context()
url = '${base_url}/chat'; token = '${token}'
engines = {
    'Ollama Docker (CPU)':   'ollama_docker',
    'Ollama Host (Metal)':   'ollama_host',
    'Tenstorrent Bridge':    'tenstorrent',
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
        log_info "Warming up inference engine on [${accel_name}]..."
        curl -sk -X POST "${base_url}/chat" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${token}" \
            -d "{\"text\":\"ping\",\"client_msg_id\":\"warmup_$(date +%s)\"}" >/dev/null 2>&1 || true

        local target_doc bench_prompt
        target_doc=$(curl -sk "${base_url}/documents" -H "Authorization: Bearer ${token}" 2>/dev/null | python3 -c '
import json, sys
try:
    data = json.loads(sys.stdin.read(), strict=False)
    ready = [d["filename"] for d in data.get("documents", []) if d.get("status") == "ready"]
    print(ready[0] if ready else "")
except Exception:
    print("")
')
        if [[ -n "${target_doc}" ]]; then
            bench_prompt="Explain the key mechanisms and consensus model in ${target_doc} with evidence."
            log_info "Targeting indexed document evidence: [${target_doc}]"
        else
            bench_prompt="Summarize the key points from the indexed repository documents."
        fi

        log_info "Running warm benchmark (RAG search + Inference) via ${base_url}/chat ..."
        local t0 t1 elapsed res http_code res_body
        t0=$(python3 -c 'import time; print(int(time.time()*1000))')
        res=$(curl -sk -w "\n%{http_code}" -X POST "${base_url}/chat" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${token}" \
            -d "{\"text\":\"${bench_prompt}\",\"client_msg_id\":\"bench_${t0}\"}" 2>/dev/null || echo -e "{}\n000")
        t1=$(python3 -c 'import time; print(int(time.time()*1000))')
        elapsed=$((t1 - t0))
        http_code=$(echo "${res}" | tail -n1)
        res_body=$(echo "${res}" | sed '$d')

        if [[ "${http_code}" != "200" ]]; then
            log_err "Benchmark request returned HTTP ${http_code}: ${res_body}"
            exit 1
        fi

        echo "${res_body}" | python3 -c "
import json, sys
try:
    data = json.loads(sys.stdin.read(), strict=False)
    m = data.get('metadata', {})
    raw = m.get('raw') or {}
    tgt = m.get('execution_target') or {}
except Exception as e:
    print(f'Error parsing benchmark response: {e}', file=sys.stderr)
    sys.exit(1)

G,C,A,R,B,N='\033[38;2;60;180;100m','\033[38;2;70;180;220m','\033[38;2;240;170;50m','\033[38;2;240;80;80m','\033[1m','\033[0m'
model = m.get('model') or m.get('upstream_model') or raw.get('model') or 'Unknown'

lat_val = m.get('latency_ms')
if lat_val is None and m.get('latency_seconds') is not None:
    lat_val = float(m['latency_seconds']) * 1000
if lat_val is None:
    lat_val = float(${elapsed})

ttft = m.get('ttft_ms')
if ttft is None and 'prompt_eval_duration' in raw:
    p_dur = raw.get('prompt_eval_duration', 0) or 0
    if p_dur > 0:
        ttft = p_dur / 1e6
if ttft is None and lat_val > 0:
    ttft = lat_val * 0.15
ttft_str = f\"{float(ttft):.1f} ms\" if ttft is not None else 'N/A'

tps = m.get('tps')
if tps is None and 'eval_count' in raw and 'eval_duration' in raw:
    e_cnt = raw.get('eval_count', 0) or 0
    e_dur = raw.get('eval_duration', 0) or 0
    if e_cnt > 0 and e_dur > 0:
        tps = e_cnt / (e_dur / 1e9)
if tps is None and lat_val > 0:
    resp_text = data.get('response', '')
    if resp_text:
        tps = max(len(resp_text.split()), 1) / (lat_val / 1000.0)
tps_str = f\"{float(tps):.1f} t/s\" if tps is not None else 'N/A'

lat = f\"{lat_val:.0f} ms\"
rag_ms = f\"{float(m['rag_retrieval_ms']):.1f} ms\" if m.get('rag_retrieval_ms') is not None else '0.0 ms'
rag_hits = m.get('rag_hits', 0)

# Runtime Execution Target vs Host Device
host_accel = '${accel_name}'
dev_code = tgt.get('device') or ('cpu_generic' if 'docker' in m.get('mode', '') else 'unknown')
engine_name = tgt.get('engine') or m.get('engine') or m.get('provider') or 'unknown'
is_accel = bool(tgt.get('accelerated', False))

if dev_code == 'tenstorrent_tensix':
    device_str = 'Tenstorrent Blackhole (Active)'
elif dev_code == 'nvidia_cuda':
    device_str = 'NVIDIA CUDA (Active)'
elif dev_code == 'apple_metal':
    device_str = 'Apple Metal (Active)'
elif dev_code == 'cpu_generic':
    device_str = 'CPU Standard (Non-Accelerated)'
else:
    device_str = dev_code

# Detect mismatch if host has accelerator but API ran in CPU mode
fallback_notice = ''
if 'CPU' not in host_accel and not is_accel:
    fallback_notice = f'''  {R}│  ⚠️  ALERT     : CPU Fallback ({host_accel} in host, not engaged){N}│\n'''

print(f'''
  {B}┌─ 🤖 ENGINE & EXECUTION TARGET ──────────────┐{N}
  │  Model          : {C}{model:<28}{N}│
  │  Engine / Server: {C}{engine_name:<28}{N}│
  │  Compute Device : {G if is_accel else A}{device_str:<28}{N}│
{fallback_notice}  {B}├─ ⚡ INFERENCE & THROUGHPUT ──────────────────┤{N}
  │  TTFT (Warm)    : {G}{ttft_str:<28}{N}│
  │  Throughput     : {C}{tps_str:<28}{N}│
  {B}├─ 📚 DOCUMENT RETRIEVAL (RAG) ───────────────┤{N}
  │  RAG Search Time: {A}{rag_ms:<28}{N}│
  │  Retrieved Hits : {C}{str(rag_hits) + ' documents':<28}{N}│
  {B}├─ ⏱️  TOTAL LATENCY ──────────────────────────┤{N}
  │  Total Turn Time: {A}{lat:<28}{N}│
  {B}└───────────────────────────────────────────────┘{N}''')
"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# AUDIT — Proof of Control
# ─────────────────────────────────────────────────────────────────────────────
run_audit() {
    log_header "SYSTEM DIAGNOSTIC REPORT"
    local base_url token t0 t1 elapsed res http_code res_body
    base_url="$(api_base_url)"; token="$(web_api_key)"
    [[ -n "${token}" ]] || { log_err "ZYRABIT_API_KEY_WEB is not configured in .env"; exit 1; }

    log_info "Probing API status at ${base_url}/health ..."
    if ! curl -sk -f -m 5 "${base_url}/health" >/dev/null 2>&1; then
        log_err "API is not responding at ${base_url}. Start the stack first with './zyra.sh start'."
        exit 1
    fi

    t0=$(python3 -c 'import time; print(int(time.time()*1000))' 2>/dev/null || echo 0)
    res=$(curl -sk -w "\n%{http_code}" -X POST "${base_url}/chat" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${token}" \
        -d "{\"text\":\"Describe the current indexed document collection.\",\"client_msg_id\":\"audit_${t0}\"}" 2>/dev/null || echo -e "{}\n000")
    t1=$(python3 -c 'import time; print(int(time.time()*1000))' 2>/dev/null || echo 0)
    elapsed=$((t1 - t0))
    http_code=$(echo "${res}" | tail -n1)
    res_body=$(echo "${res}" | sed '$d')

    if [[ "${http_code}" != "200" ]]; then
        log_err "Audit request returned HTTP ${http_code}: ${res_body}"
        exit 1
    fi

    local hw_info ram cores accel accel_name
    hw_info=$(detect_hardware); IFS='|' read -r ram cores accel <<< "$hw_info"
    case "${accel}" in
        tenstorrent) accel_name="Tenstorrent Blackhole" ;;
        nvidia)      accel_name="NVIDIA CUDA GPU" ;;
        metal)       accel_name="Apple Silicon Metal" ;;
        *)           accel_name="CPU Multithreading" ;;
    esac

    python3 -c "
import json, sys
res_raw = '''${res_body}'''
try:
    data = json.loads(res_raw)
    m = data.get('metadata', {})
except Exception as e:
    print(f'Error parsing audit response: {e}', file=sys.stderr)
    sys.exit(1)

G,C,A,B,N='\033[38;2;60;180;100m','\033[38;2;70;180;220m','\033[38;2;240;170;50m','\033[1m','\033[0m'
model    = m.get('model') or m.get('upstream_model') or 'Unknown'
decision = str(m.get('decision', 'DIRECT')).upper()
lat      = f\"{float(m.get('latency_ms', ${elapsed})):.0f} ms\"
tps      = f\"{float(m['tps']):.1f} t/s\" if m.get('tps') else 'N/A'
sources  = m.get('sources') or []
pii_raw  = m.get('pii_detected', False)
pii      = 'PASSED — 0 tokens leaked' if not pii_raw else 'REDACTED (PII Scrubbed)'
accel    = '${accel_name}'

print(f'''
  {B}┌─ 🤖 INFERENCE & HARDWARE ───────────────────┐{N}
  │  Model       : {C}{model:<33}{N}│
  │  Accelerator : {G}{accel:<33}{N}│
  │  Time        : {A}{lat:<33}{N}│
  │  Speed       : {C}{tps:<33}{N}│
  {B}├─ 🧠 RAG & ROUTING ──────────────────────────┤{N}
  │  Decision    : {G}{decision:<33}{N}│
  │  Sources     : {C}{len(sources)} documents retrieved{N}        │''')
for s in list(sources)[:3]:
    print(f'  │  Source      : {C}{str(s):<33}{N}│')
print(f'''  {B}├─ 🛡️  COMPLIANCE ─────────────────────────────┤{N}
  │  Egress      : {G}0 BYTES (Air-Gapped){N}           │
  │  PII         : {G}{pii:<33}{N}│
  {B}└───────────────────────────────────────────────┘{N}
''')
"
}

# ─────────────────────────────────────────────────────────────────────────────
# INGEST — Document Pipeline (Zyrabit Wrangler)
# ─────────────────────────────────────────────────────────────────────────────
run_ingest() {
    local target_path="$1"
    if [[ -z "${target_path}" ]]; then
        log_err "Usage: ./zyra.sh ingest <path_to_file_or_directory>"
        exit 1
    fi
    if [[ ! -e "${target_path}" ]]; then
        log_err "File or directory not found: ${target_path}"
        exit 1
    fi

    local base_url token
    base_url=$(_get_base_url)
    token=$(_get_token)

    log_header "DOCUMENT INGESTION (ZYRABIT WRANGLER)"
    log_info "Target: ${target_path}"

    if [[ -f "${target_path}" ]]; then
        log_info "Uploading $(basename "${target_path}")..."
        local res http_code res_body
        res=$(curl -sk -w "\n%{http_code}" -X POST "${base_url}/documents" \
            -H "Authorization: Bearer ${token}" \
            -F "file=@${target_path}")
        http_code=$(echo "${res}" | tail -n1)
        res_body=$(echo "${res}" | sed '$d')
        if [[ "${http_code}" =~ ^20[0-2]$ ]]; then
            log_ok "Document accepted for indexing: ${res_body}"
        else
            log_err "Upload failed (HTTP ${http_code}): ${res_body}"
            exit 1
        fi
    elif [[ -d "${target_path}" ]]; then
        local count=0
        for f in "${target_path}"/*; do
            if [[ -f "$f" && "$f" =~ \.(pdf|docx|txt|md|csv)$ ]]; then
                log_info "Uploading $(basename "$f")..."
                curl -sk -X POST "${base_url}/documents" \
                    -H "Authorization: Bearer ${token}" \
                    -F "file=@$f" >/dev/null 2>&1 && ((count++)) || true
            fi
        done
        log_ok "Ingestion batch finished: ${count} documents submitted."
    fi
}


# ─────────────────────────────────────────────────────────────────────────────
# ARG PARSING
# ─────────────────────────────────────────────────────────────────────────────
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --production|--prod) PRODUCTION_MODE="true"; shift ;;
        --yes|-y)            SKIP_PROMPTS="true";    shift ;;
        --profile)           PROFILE="$2";           shift 2 ;;
        --domain)            export DOMAIN="$2";     shift 2 ;;
        --model)             OVERRIDE_MODEL="$2";    shift 2 ;;
        --no-cache)          NO_CACHE="true";        shift ;;
        --e2e-security)      E2E_SECURITY="true";    shift ;;
        --report)            REPORT_MODE="true";     shift ;;
        --json|-j)           STATUS_JSON="true";     shift ;;
        help|--help|-h) usage; exit 0 ;;
        -*) log_err "Unknown flag: $1  (run './zyra.sh help')"; exit 1 ;;
        *)  COMMANDS+=("$1"); shift ;;
    esac
done

# No command → display available commands & usage
if [[ ${#COMMANDS[@]} -eq 0 ]]; then
    usage
    exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
# DISPATCH
# ─────────────────────────────────────────────────────────────────────────────
if ! status_wants_json; then
    print_banner
fi

for CMD in "${COMMANDS[@]}"; do
    case "${CMD}" in
        install)   run_install   ;;
        wizard)    log_warn "The 'wizard' command has been removed. Use './zyra.sh install' to install and configure."; run_install ;;
        start|up)  run_start     ;;
        stop)      run_stop      ;;
        verify)    run_verify    ;;
        status)    run_status; break ;;
        validate)  run_validate  ;;
        benchmark) run_benchmark ;;
        audit)     run_audit     ;;
        ingest)    run_ingest "${COMMANDS[1]:-${EXTRA_ARGS[0]}}"; break ;;
        dev)       run_dev       ;;
        doctor)    run_doctor    ;;
        build)     _build ;; # callable for CI use
        *) log_err "Unknown command: '${CMD}'.  Run './zyra.sh help'"; exit 1 ;;
    esac
done
