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

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  log_err "docker-compose file not found at ${COMPOSE_FILE}"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  log_err "Docker is required."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  log_err "Docker daemon is not running."
  exit 1
fi

MODEL_DEFAULT="${ZYRABIT_MODEL_DEFAULT:-qwen2.5:7b}"
MODEL_LOW_RAM="${ZYRABIT_MODEL_LOW_RAM:-qwen2.5:1.5b}"
RAM_GB="$(($(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1024 / 1024 / 1024))"
if [[ "${RAM_GB}" -gt 0 && "${RAM_GB}" -lt 12 ]]; then
  MODEL_DEFAULT="${MODEL_LOW_RAM}"
fi
MODEL_NAME="${ZYRABIT_MODEL:-${MODEL_DEFAULT}}"

ACCELERATOR="cpu"
if command -v nvidia-smi >/dev/null 2>&1; then
  ACCELERATOR="nvidia"
elif [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
  ACCELERATOR="metal"
fi

log_info "Selected model: ${MODEL_NAME}"
log_info "Detected accelerator: ${ACCELERATOR}"

case "${ACCELERATOR}" in
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
    if [[ -z "${ZYRABIT_MODEL:-}" ]]; then
      MODEL_NAME="${MODEL_LOW_RAM}"
      log_info "Auto-switching to low RAM model: ${MODEL_NAME}"
    fi
    ;;
esac

log_info "Starting secure stack via Docker Compose..."
docker compose -f "${COMPOSE_FILE}" up -d
log_ok "Infrastructure started."

log_info "Waiting for SLM endpoint..."
for _ in {1..30}; do
  if docker compose -f "${COMPOSE_FILE}" exec -T slm-engine ollama list >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

log_info "Ensuring base models are present..."
docker compose -f "${COMPOSE_FILE}" exec -T slm-engine ollama pull "${MODEL_NAME}"
docker compose -f "${COMPOSE_FILE}" exec -T slm-engine ollama pull "mxbai-embed-large"

log_ok "Zyrabit is ready."
echo
echo "API (Traefik HTTPS): https://localhost/health"
echo "Prometheus: http://localhost:9091"
echo "Grafana: http://localhost:3000"
