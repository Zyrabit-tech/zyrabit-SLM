#!/usr/bin/env bash

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_ok() { echo -e "${GREEN}✔${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_err() { echo -e "${RED}✖${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/zyrabit-brain-api/docker-compose.yml"
ENV_FILE="${SCRIPT_DIR}/zyrabit-brain-api/.env"

usage() {
  cat <<'EOF'
Usage: ./zyra-up.sh [command] [options]

Commands:
  install   Start stack and pull required models (default)
  start     Start stack only
  doctor    Validate environment and print detected runtime profile
  help      Show this help message

Options:
  --profile <name>  Start Docker Compose with a specific profile (e.g., n8n, docs, observability-extra)
EOF
}

require_compose_file() {
  if [[ ! -f "${COMPOSE_FILE}" ]]; then
    log_err "docker-compose file not found at ${COMPOSE_FILE}"
    exit 1
  fi
}

read_env_value() {
  local key="$1"
  if [[ ! -f "${ENV_FILE}" ]]; then
    return 0
  fi
  awk -F= -v key="${key}" '
    /^[[:space:]]*#/ {next}
    $1 ~ "^[[:space:]]*" key "[[:space:]]*$" {
      sub(/^[^=]*=/, "", $0)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", $0)
      print $0
      exit
    }
  ' "${ENV_FILE}"
}

resolve_required_var_value() {
  local var_name="$1"
  local runtime_value file_value

  if [[ "${!var_name+x}" == "x" ]]; then
    runtime_value="${!var_name}"
    printf '%s' "${runtime_value}"
    return 0
  fi

  file_value="$(read_env_value "${var_name}")"
  printf '%s' "${file_value}"
}

validate_required_env_vars() {
  local required_vars=(
    "SLM_URL"
    "DB_URL"
    "MODEL_NAME"
  )

  for var_name in "${required_vars[@]}"; do
    local value value_lower
    value="$(resolve_required_var_value "${var_name}")"
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"

    if [[ -z "${value}" ]]; then
      log_err "Required variable '${var_name}' is missing or empty (runtime env or ${ENV_FILE})"
      exit 1
    fi

    value_lower="$(printf '%s' "${value}" | tr '[:upper:]' '[:lower:]')"
    case "${value_lower}" in
      undefined|null|none)
        log_err "Variable '${var_name}' has invalid value '${value}' (runtime env or ${ENV_FILE})"
        exit 1
        ;;
    esac
  done
}

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    log_err "Docker is required."
    exit 1
  fi

  if ! docker info >/dev/null 2>&1; then
    log_err "Docker daemon is not running."
    exit 1
  fi
}

detect_ram_gb() {
  if [[ "$(uname -s)" == "Darwin" ]]; then
    echo "$(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1024 / 1024 / 1024 ))"
    return
  fi

  if [[ -f "/proc/meminfo" ]]; then
    local mem_kb
    mem_kb="$(awk '/MemTotal/ {print $2}' /proc/meminfo)"
    echo "$(( mem_kb / 1024 / 1024 ))"
    return
  fi

  echo "0"
}

detect_accelerator() {
  if command -v nvidia-smi >/dev/null 2>&1; then
    echo "nvidia"
    return
  fi
  if [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
    echo "metal"
    return
  fi
  echo "cpu"
}

resolve_model_name() {
  local model_default model_low_ram ram_gb
  model_default="${ZYRABIT_MODEL_DEFAULT:-qwen2.5:7b}"
  model_low_ram="${ZYRABIT_MODEL_LOW_RAM:-qwen2.5:1.5b}"
  ram_gb="$(detect_ram_gb)"

  if [[ "${ram_gb}" -gt 0 && "${ram_gb}" -lt 12 ]]; then
    model_default="${model_low_ram}"
  fi

  if [[ -n "${ZYRABIT_MODEL:-}" ]]; then
    echo "${ZYRABIT_MODEL}"
  else
    echo "${model_default}"
  fi
}

apply_accelerator_profile() {
  local accelerator="$1"
  case "${accelerator}" in
    nvidia)
      log_ok "NVIDIA GPU detected. Using CUDA-capable container runtime if configured."
      export OLLAMA_NUM_GPU=999
      ;;
    metal)
      log_ok "Apple Silicon detected. Optimizing for Metal backend."
      export OLLAMA_NUM_GPU=1
      ;;
    *)
      log_warn "CPU-only mode detected. Quantized model is recommended."
      ;;
  esac
}

run_start() {
  require_compose_file
  validate_required_env_vars
  require_docker
  
  local compose_args=("-f" "${COMPOSE_FILE}")
  
  if [[ -n "${PROFILE}" ]]; then
    if [[ "${PROFILE}" == "n8n" ]]; then
       PROFILE="automation"
    fi
    compose_args+=("--profile" "${PROFILE}")
    log_info "Starting secure stack via Docker Compose with profile: ${PROFILE}..."
  else
    log_info "Starting secure stack via Docker Compose..."
  fi
  
  compose_args+=("up" "-d")
  docker compose "${compose_args[@]}"
  log_ok "Infrastructure started."
}

run_install() {
  local accelerator model_name
  accelerator="$(detect_accelerator)"
  model_name="$(resolve_model_name)"

  log_info "Selected model: ${model_name}"
  log_info "Detected accelerator: ${accelerator}"
  apply_accelerator_profile "${accelerator}"
  run_start

  log_info "Waiting for SLM endpoint..."
  for _ in {1..30}; do
    if docker compose -f "${COMPOSE_FILE}" exec -T slm-engine ollama list >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done

  log_info "Ensuring base models are present..."
  docker network connect zyrabit-brain-api_backend-network slm-engine || true
  docker compose -f "${COMPOSE_FILE}" exec -T slm-engine ollama pull "${model_name}"
  docker compose -f "${COMPOSE_FILE}" exec -T slm-engine ollama pull "mxbai-embed-large"
  docker network disconnect zyrabit-brain-api_backend-network slm-engine || true

  log_ok "Zyrabit is ready."
  echo
  echo "API (Traefik HTTPS): https://localhost/health"
  echo "Prometheus (Traefik): https://localhost/prometheus"
  echo "Grafana (Traefik): https://localhost/grafana"
}

run_doctor() {
  local accelerator model_name ram_gb
  require_compose_file
  validate_required_env_vars
  ram_gb="$(detect_ram_gb)"
  accelerator="$(detect_accelerator)"
  model_name="$(resolve_model_name)"

  echo "Zyrabit Doctor"
  echo "--------------"
  echo "compose_file: ${COMPOSE_FILE}"
  echo "ram_gb: ${ram_gb}"
  echo "accelerator: ${accelerator}"
  echo "selected_model: ${model_name}"

  if command -v docker >/dev/null 2>&1; then
    echo "docker: installed"
    if docker info >/dev/null 2>&1; then
      echo "docker_daemon: running"
    else
      echo "docker_daemon: not_running"
    fi
  else
    echo "docker: missing"
  fi
}

PROFILE=""
COMMAND="install"

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    install|start|doctor|help|-h|--help)
      COMMAND="$1"
      shift
      ;;
    *)
      log_err "Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

case "${COMMAND}" in
  install)
    run_install
    ;;
  start)
    run_start
    ;;
  doctor)
    run_doctor
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    log_err "Unknown command: ${COMMAND}"
    usage
    exit 1
    ;;
esac
