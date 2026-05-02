#!/bin/bash

# Zyrabit SLM - Local Dev Launcher (UV Optimized)
# -----------------------------------------------

# 1. Check for 'uv' (The pnpm of Python)
if ! command -v uv &> /dev/null; then
    echo "❌ 'uv' is not installed."
    echo "💡 Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "🚀 Initializing Zyrabit Environment (Python 3.12 via uv)..."

# 2. Ensure Virtual Environment with Python 3.12
if [ ! -d ".venv" ]; then
    uv venv --python 3.12
fi
source .venv/bin/activate

# 3. Fast Sync Dependencies
echo "📦 Syncing dependencies..."
uv pip install -r api-rag/requirements.txt

# 4. Set Dev Environment Variables
export DB_HOST="127.0.0.1"
export DB_PORT="8000"
export SLM_URL="http://localhost:11434"
export APP_ENV="local"

# 5. Launch API with Hot-Reload
echo "🔥 Launching Zyrabit API in Local Dev Mode..."
cd api-rag && uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
