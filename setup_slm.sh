#!/usr/bin/env bash

# ==============================================================================
# 🛡️ Zyrabit SLM Engine Setup Script
# ==============================================================================
# Description:
#   Orchestrates the initialization of the local AI engine via Docker.
#   1. Validates Docker environment.
#   2. Locates the correct infrastructure configuration.
#   3. Ensures the SLM engine container is running.
#   4. Downloads required models (SLM + Embeddings) directly into the volume.
#
# Usage:
#   chmod +x setup_slm.sh
#   ./setup_slm.sh
# ==============================================================================

# --- Style & Colors ---
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Helper Functions ---
log_info()    { echo -e "${BLUE}ℹ $1${NC}"; }
log_success() { echo -e "${GREEN}✔ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
log_error()   { echo -e "${RED}✖ $1${NC}"; }

# --- Configuration ---
REQUIRED_MODELS=(
  "phi3"
  "kimi-k2-thinking:cloud"
  "mxbai-embed-large"
)

echo -e "${YELLOW}🐳 Starting Zyrabit SLM Engine Setup...${NC}"

# 1. Locate Docker Compose Configuration
COMPOSE_FILE=""
if [ -f "zyrabit-brain-api/docker-compose.yml" ]; then
    COMPOSE_FILE="zyrabit-brain-api/docker-compose.yml"
elif [ -f "docker-compose.yml" ]; then
    COMPOSE_FILE="docker-compose.yml"
else
    log_error "Critical: 'docker-compose.yml' not found."
    exit 1
fi

# 2. Verify Docker Daemon
if ! docker info > /dev/null 2>&1; then
  log_error "Docker is not running."
  exit 1
fi
log_success "Docker daemon is active."

# 3. Ensure Container State
log_info "Verifying container 'slm-engine' status..."
CONTAINER_ID=$(docker compose -f "$COMPOSE_FILE" ps -q slm-engine)

if [ -z "$CONTAINER_ID" ]; then
    log_warning "Container not created. Bringing up infrastructure..."
    docker compose -f "$COMPOSE_FILE" up -d slm-engine
    CONTAINER_ID=$(docker compose -f "$COMPOSE_FILE" ps -q slm-engine)
fi

IS_RUNNING=$(docker inspect -f '{{.State.Running}}' "$CONTAINER_ID" 2>/dev/null)
if [ "$IS_RUNNING" != "true" ]; then
    log_warning "Container stopped. Restarting..."
    docker compose -f "$COMPOSE_FILE" start slm-engine
    sleep 2
fi
log_success "SLM Engine container is running."

# 4. Wait for API Availability
HOST="localhost"
PORT=11434
MAX_RETRIES=15
RETRY=0

log_info "Waiting for SLM API to accept connections on port ${PORT}..."
until curl -s -f "http://${HOST}:${PORT}/api/tags" > /dev/null; do
  if [ $RETRY -ge $MAX_RETRIES ]; then
    log_error "Timeout: SLM service not reachable."
    exit 1
  fi
  sleep 2
  RETRY=$((RETRY+1))
done
log_success "Connection established with SLM Engine."

# 5. Pull Models
log_info "Syncing required models..."

for MODEL in "${REQUIRED_MODELS[@]}"; do
  log_info "Checking/Pulling model: '${MODEL}'..."
  
  # --- CORRECCIÓN AQUÍ: Usamos 'ollama', no 'slm' ---
  if docker compose -f "$COMPOSE_FILE" exec -T slm-engine ollama pull "$MODEL"; then
    log_success "Model '${MODEL}' is ready."
  else
    log_error "Failed to pull model '${MODEL}'."
    exit 1
  fi
done

echo -e "${GREEN}🎉 Zyrabit SLM Engine is set up and ready!${NC}"