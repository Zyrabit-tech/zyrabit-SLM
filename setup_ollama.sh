#!/usr/bin/env bash

# setup_ollama.sh - Robust installer for required Ollama models
# ------------------------------------------------------------
# Checks Docker daemon, ensures SLM-server container is running,
# waits for Ollama port 11434, then pulls required models.
# Uses ANSI colors for feedback.

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper functions
log_success() { echo -e "${GREEN}✔ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
log_error()   { echo -e "${RED}✖ $1${NC}"; }

# 1. Verify Docker is running
if ! docker info > /dev/null 2>&1; then
  log_error "Docker does not appear to be running. Please start Docker and retry."
  exit 1
fi
log_success "Docker daemon is active."

# 2. Ensure SLM-server container exists
CONTAINER_NAME="SLM-server"
if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  log_error "Container '${CONTAINER_NAME}' not found. Ensure it is defined in docker-compose.yml and run 'docker compose up -d'."
  exit 1
fi

# 3. Start container if it is stopped/exited
STATUS=$(docker inspect -f '{{.State.Status}}' ${CONTAINER_NAME})
if [ "$STATUS" != "running" ]; then
  log_warning "Container '${CONTAINER_NAME}' is $STATUS. Attempting to start..."
  docker compose start ${CONTAINER_NAME}
  if [ $? -ne 0 ]; then
    log_error "Failed to start '${CONTAINER_NAME}'."
    exit 1
  fi
fi
log_success "Container '${CONTAINER_NAME}' is running."

# 4. Wait for Ollama port 11434 to be reachable
HOST="localhost"
PORT=11434
MAX_RETRIES=30
RETRY=0
while ! curl -s "http://${HOST}:${PORT}/api/heartbeat" > /dev/null; do
  RETRY=$((RETRY+1))
  if [ $RETRY -ge $MAX_RETRIES ]; then
    log_error "Ollama service did not become reachable on ${HOST}:${PORT} after $MAX_RETRIES attempts."
    exit 1
  fi
  log_warning "Waiting for Ollama (${HOST}:${PORT})... (${RETRY}/${MAX_RETRIES})"
  sleep 2
done
log_success "Ollama is reachable on ${HOST}:${PORT}."

# 5. Pull required models
MODELS=(
  "phi3"
  "kimi-k2-thinking:cloud"
  "mxbai-embed-large"
)
for MODEL in "${MODELS[@]}"; do
  log_warning "Pulling model '${MODEL}'..."
  if ollama pull "$MODEL"; then
    log_success "Model '${MODEL}' pulled successfully."
  else
    log_error "Failed to pull model '${MODEL}'."
    exit 1
  fi
done

log_success "All models have been installed."

# End of script
