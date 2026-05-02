#!/bin/bash

# Zyrabit SLM: Local Development Launcher
# This script runs the API natively on your Mac for instant feedback.

echo "🚀 Launching Zyrabit API in Local Dev Mode (Hot-Reload)..."

# 1. Environment Overrides
export PROJECT_NAME="Zyrabit-Dev"
export SLM_URL="http://localhost:11434"
export DB_HOST="127.0.0.1"
export DB_PORT=8000
export RAG_COLLECTION="zyrabit_knowledge"
export MODEL_NAME="qwen2.5:7b"

# 2. Path Setup
export PYTHONPATH=$PYTHONPATH:$(pwd)/api-rag

# 3. Execution
cd api-rag && uvicorn app.main:app --reload --port 8081 --host 0.0.0.0
