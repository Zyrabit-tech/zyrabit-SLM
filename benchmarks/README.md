# Benchmarks — Tenstorrent Blackhole (p150)

**Real** inference results measured on local lab Tenstorrent Blackhole p150 hardware, serving through the bridge (`internal/engine/tenstorrent`) in `metal` mode.

## Hardware

- **Accelerator**: Tenstorrent Blackhole (p150), driver `tenstorrent.ko`.
- **Engine**: vLLM-TT (`ghcr.io/tenstorrent/tt-inference-server/vllm-tt-metal-src-release-ubuntu-22.04-amd64:0.8.0-55fd115-aa4ae1e`).
- **Target Model on single p150 device**: `Qwen/Qwen2.5-3B-Instruct` (Qwen2.5-7B requires 2-4 devices and does not fit on a single p150).

## How to Capture

```bash
# 1) Start physical stack (see internal/engine/tenstorrent/README.md)
docker compose -f zyrabit-slm/docker-compose.yml --profile tenstorrent up -d

# 2) End-to-end benchmark (API RAG -> bridge -> engine)
./zyra.sh benchmark

# 3) Structured capture against the bridge
./benchmarks/capture_tt_benchmark.sh http://localhost:8090 benchmarks/results/p150-qwen25-3b.json
```

## Results

- `results/p150-qwen25-3b.json` — metrics captured from the p150 (TTFT, tps, latency).

## Note

Historical benchmarks (`docs-portal/docs/benchmarks.md`) correspond to the simulated stack; data from this point forward represents physical hardware execution.
