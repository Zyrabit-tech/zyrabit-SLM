#!/bin/bash
# Launcher for the vLLM-TT engine (Blackhole p150) via tt-inference-server wrapper.
set -e

source "${PYTHON_ENV_DIR}/bin/activate"

export TT_MODEL_SPEC_JSON_PATH=/model_spec.json
export CACHE_ROOT=/home/container_app_user/cache_root
export TT_CACHE_PATH="${CACHE_ROOT}/tt_cache"

# Resolve the HF snapshot dir inside the offline cache (HF_HUB_OFFLINE=1).
MODEL_SNAP="$(ls -d /hf-cache/hub/models--Qwen--Qwen2.5-3B-Instruct/snapshots/*/ 2>/dev/null | head -1 | sed 's:/$::')"
if [ -z "${MODEL_SNAP}" ]; then
    echo "ERROR: Qwen2.5-3B-Instruct not found in /hf-cache (download incomplete?)" >&2
    exit 1
fi
export MODEL_WEIGHTS_PATH="${MODEL_SNAP}"
echo "MODEL_WEIGHTS_PATH=${MODEL_WEIGHTS_PATH}"

exec python /home/container_app_user/app/src/run_vllm_api_server.py
