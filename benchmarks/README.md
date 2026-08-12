# Benchmarks — Tenstorrent Blackhole (p150)

Resultados de inferencia **reales** medidos en el hardware Tenstorrent Blackhole
p150 del laboratorio local, sirviendo a traves del bridge
(`internal/engine/tenstorrent`) en modo `metal`.

## Hardware

- Acelerador: Tenstorrent Blackhole (p150), driver `tenstorrent.ko`.
- Motor: vLLM-TT (`ghcr.io/tenstorrent/tt-inference-server/vllm-tt-metal-src-release-ubuntu-22.04-amd64:0.8.0-55fd115-aa4ae1e`).
- Modelo objetivo en este p150 (single device): `Qwen/Qwen2.5-3B-Instruct`
  (Qwen2.5-7B requiere 2-4 dispositivos y no cabe en un solo p150).

## Como capturar

```bash
# 1) Stack real arriba (ver internal/engine/tenstorrent/README.md)
docker compose -f zyrabit-slm/docker-compose.yml --profile tenstorrent up -d

# 2) Benchmark end-to-end (API RAG -> bridge -> engine)
./zyra.sh benchmark

# 3) Captura estructurada contra el bridge
./benchmarks/capture_tt_benchmark.sh http://localhost:8090 benchmarks/results/p150-qwen25-3b.json
```

## Resultados

- `results/p150-qwen25-3b.json` — metrica capturada del p150 (TTFT, tps, latencia).

## Nota

Los benchmarks historicos (`docs-portal/docs/benchmarks.md`) corresponden al
stack simulado; a partir de aqui los datos son de hardware real.
