#!/bin/bash
# run_local_tt_tests.sh - Script de benchmarking para simulador Tenstorrent (Golden Model)
set -e

# Configuración actualizada para evitar OOM (Out of Memory) en Mac
CONTAINER_NAME="zyrabit-tt-bridge"
MODEL_ID="Qwen/Qwen2.5-1.5B-Instruct"
HF_CACHE_DIR="/root/.cache/huggingface/hub"
PYTHON_SCRIPT_PATH="/tmp/test_tt_inference.py"
LOG_FILE="tt_compiler_output.log"

echo "=========================================================="
echo "  Iniciando Benchmarking Local: Zyrabit TT Bridge (Sim)"
echo "  Modelo Target: $MODEL_ID"
echo "=========================================================="

echo "[1/4] Verificando entorno Docker..."
if ! docker ps --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}\$"; then
    echo "ERROR: El contenedor no está corriendo."
    exit 1
fi
echo "✅ Contenedor $CONTAINER_NAME en ejecución."

echo "[2/4] Verificando/Descargando pesos del modelo..."
# Dado que zyrabit-tt-bridge vive en una red Zero-Trust (model-network) sin internet,
# usamos un contenedor efímero temporal con internet para descargar al volumen compartido.
HF_CACHE_HOST_DIR="/Users/abrahamgomez/tech/zyrabit-SLM/zyrabit-slm/hf-cache"
mkdir -p "$HF_CACHE_HOST_DIR"

docker run --rm -e HF_HOME=/root/.cache/huggingface/hub -v "$HF_CACHE_HOST_DIR":/root/.cache/huggingface/hub python:3.11-slim bash -c "
    pip install -q huggingface_hub && \
    hf download $MODEL_ID
"
echo "✅ Modelo listo en caché compartida."

echo "[3/4] Generando script de inferencia seguro (bfloat16)..."
docker exec $CONTAINER_NAME bash -c "cat << 'EOF' > $PYTHON_SCRIPT_PATH
import os
import time
import torch
import torch_xla.core.xla_model as xm
from transformers import AutoModelForCausalLM, AutoTokenizer

os.environ['INFERENCE_PROVIDER'] = 'tt-forge-sim'
os.environ['PJRT_DEVICE'] = 'TT'
os.environ['XLA_STABLEHLO_COMPILE'] = '1'

model_id = os.environ.get('MODEL_ID', 'Qwen/Qwen2.5-1.5B-Instruct')
cache_dir = os.environ.get('HF_CACHE_DIR', '/root/.cache/huggingface/hub')

tokenizer = AutoTokenizer.from_pretrained(model_id, cache_dir=cache_dir)
model = AutoModelForCausalLM.from_pretrained(
    model_id, 
    cache_dir=cache_dir, 
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True
)

device = xm.xla_device()
model.to(device)

prompt = 'Zyrabit SLM architecture with Tenstorrent is designed to provide'
inputs = tokenizer(prompt, return_tensors='pt').to(device)

start_time = time.time()
with torch.no_grad():
    outputs = model.generate(**inputs, max_new_tokens=5)

xm.sync(wait=True)
end_time = time.time()

print(f'--> Tiempo: {end_time - start_time:.4f}s')
print('--> Salida:', tokenizer.decode(outputs[0], skip_special_tokens=True))
EOF"

echo "[4/4] Ejecutando test e interceptando métricas del compilador..."
rm -f $LOG_FILE

docker exec \
    -e MODEL_ID="$MODEL_ID" \
    -e HF_CACHE_DIR="$HF_CACHE_DIR" \
    $CONTAINER_NAME python $PYTHON_SCRIPT_PATH > $LOG_FILE 2>&1

CYCLE_COUNTS=$(grep -i "Cycle Counts" $LOG_FILE | tail -n 1 | grep -oEo '[0-9]+' || echo "No encontrado")

echo "=========================================================="
echo "  RESULTADOS DEL BENCHMARK"
echo "=========================================================="
echo "Modelo:          $MODEL_ID"
echo "Cycle Counts:    $CYCLE_COUNTS"
echo "=========================================================="

cat << EOF > tt_metrics.json
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "model": "$MODEL_ID",
  "inference_provider": "tt-forge-sim",
  "metrics": { "cycle_counts": "$CYCLE_COUNTS" }
}
EOF

echo "✅ JSON exportado con éxito en tt_metrics.json"
