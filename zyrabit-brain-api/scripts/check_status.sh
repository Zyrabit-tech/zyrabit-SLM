#!/bin/bash

# Zyrabit SLM Status Monitor
# Checks the health of all Docker containers and identifies SLM configuration.

COMPOSE_FILES="-f zyrabit-brain-api/docker-compose.yml -f zyrabit-brain-api/docker-compose.local.yml"
ENV_FILE="zyrabit-brain-api/.env"

# Load config from .env if it exists
if [ -f "$ENV_FILE" ]; then
    SLM_TARGET=$(grep "^SLM_URL=" "$ENV_FILE" | cut -d'=' -f2)
else
    SLM_TARGET="http://slm-engine:11434/api/generate" # Default
fi

echo "=========================================="
echo "   ZYRABIT SLM SYSTEM STATUS MONITOR   "
echo "=========================================="
echo ""

# 1. Configuration Info
echo "[i] Configuration Detectada:"
if [[ "$SLM_TARGET" == *"host.docker.internal"* ]]; then
    echo "    - SLM: Metal (Native App / host.docker.internal)"
elif [[ "$SLM_TARGET" == *"slm-engine"* ]]; then
    echo "    - SLM: Docker (Container-based)"
else
    echo "    - SLM: Custom ($SLM_TARGET)"
fi
echo ""

# 2. Check Container Status
echo "[+] Checking Docker containers..."
docker compose $COMPOSE_FILES ps --format "table {{.Name}}\t{{.Status}}"

echo ""
echo "[+] Connection Test (API RAG)..."

# 3. Try to hit the health endpoint directly
if curl -s -f http://localhost:8080/v1/health > /dev/null; then
    echo "SUCCESS: API RAG is responding on port 8080."
    curl -s http://localhost:8080/v1/health | python3 -m json.tool 2>/dev/null || echo "Response received but could not be parsed as JSON."
else
    echo "WAITING: API RAG is not responding on port 8080 (yet)."
    echo "If it stays like this, check logs with:"
    echo "docker compose $COMPOSE_FILES logs -f api-rag"
fi

echo ""
echo "[+] Connection Test (Ollama/SLM)..."
# Check based on configuration
if [[ "$SLM_TARGET" == *"host.docker.internal"* ]]; then
    # Checking native Ollama
    if curl -s -f http://localhost:11434/api/tags > /dev/null; then
        echo "SUCCESS: Native Ollama is responding on port 11434."
    else
        echo "ERROR: Native Ollama on port 11434 is NOT responding."
        echo "Make sure Ollama app is running on your Mac."
    fi
else
    # Checking Docker Ollama
    if curl -s -f http://localhost:11434/api/tags > /dev/null; then
        echo "SUCCESS: Docker Ollama is responding on port 11434."
    else
        echo "WAITING: Docker Ollama is not responding on port 11434."
        echo "Check if you have a native Ollama app blocking the port, or wait for the container to load models."
        echo "Logs: docker compose $COMPOSE_FILES logs -f slm-engine"
    fi
fi

echo ""
echo "=========================================="
echo "Monitor complete. Systems may take 30-60 seconds to fully initialize."
