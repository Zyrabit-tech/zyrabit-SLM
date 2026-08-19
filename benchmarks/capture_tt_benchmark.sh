#!/usr/bin/env bash
# Captura un benchmark real contra el bridge TT (metal) y lo guarda como JSON.
# Uso: ./benchmarks/capture_tt_benchmark.sh [http://localhost:8090] [resultados.json]
set -euo pipefail

BASE_URL="${1:-http://localhost:8090}"
OUT="${2:-benchmarks/results/p150-qwen25-3b.json}"
PROMPT="${PROMPT:-Summarize the indexed documents.}"

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
T0=$(python3 -c 'import time; print(int(time.time()*1000))')
RESP="$(curl -sf -X POST "${BASE_URL}/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"qwen2.5:3b\",\"messages\":[{\"role\":\"user\",\"content\":\"${PROMPT}\"}],\"max_tokens\":256}" 2>/dev/null || echo '{}')"
T1=$(python3 -c 'import time; print(int(time.time()*1000))')
TOTAL_MS=$((T1 - T0))

MODEL_IDS="$(ls /dev/tenstorrent/ 2>/dev/null | grep -c '^[0-9]*$' || echo 0)"
SYSFS_BH="$(ls /sys/class/tenstorrent/ 2>/dev/null | tr '\n' ',' || echo '')"
SERIAL="$(cat /sys/class/tenstorrent/*/serial 2>/dev/null | head -1 || echo '')"

mkdir -p "$(dirname "$OUT")"
python3 - "$RESP" "$OUT" "$TS" "$TOTAL_MS" "$MODEL_IDS" "$SYSFS_BH" "$SERIAL" <<'PYEOF'
import json, sys
resp, out, ts, total_ms, devs, sysfs, serial = sys.argv[1:8]
try:
    data = json.loads(resp)
    z = data.get("zyrabit", {})
    rec = {
        "timestamp": ts,
        "hardware": {"type": "Tenstorrent Blackhole", "board": "p150", "devices": int(devs or 0), "serial": serial, "sysfs": sysfs},
        "model": z.get("upstream_model", "Qwen/Qwen2.5-3B-Instruct"),
        "engine": z.get("engine", "vllm-tt-metalium"),
        "mode": z.get("mode"),
        "arch": z.get("arch"),
        "metrics_ms": {
            "ttft_ms": z.get("ttft_ms"),
            "tps": z.get("tps"),
            "total_ms": float(total_ms),
            "total_ms_upstream": z.get("total_ms"),
        },
        "usage": data.get("usage"),
        "answer": (data.get("choices") or [{}])[0].get("message", {}).get("content"),
    }
    print(json.dumps(rec, indent=2))
    with open(out, "w") as f:
        json.dump(rec, f, indent=2)
    print(f"\n=> {out}")
except Exception as e:
    print(f"ERROR parseando respuesta: {e}")
    print(resp[:500])
    sys.exit(1)
PYEOF
