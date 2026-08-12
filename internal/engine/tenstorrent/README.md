# Zyrabit-TT-Bridge

OpenAI-compatible bridge for inference on Tenstorrent Blackhole (p150), featuring a deterministic fallback (`mock`) for environments without physical hardware.

## Modes

- `ZYRABIT_TT_MODE=mock` (default): Responds with a simulated model, requiring no hardware.
- `ZYRABIT_TT_MODE=metal`: Proxies to an upstream vLLM-TT engine (`tt-inference-server` image), measuring real `ttft_ms` (forced stream) and calculating `tps` by counting streamed tokens (upstream vLLM-TT 0.8.0 returns `usage` as zeros; used as fallback if non-zero).
- `ZYRABIT_TT_MODE=auto`: Detects GPU via `nvidia-smi` and defaults to `mock` if unavailable.

## Variables

- `ZYRABIT_TT_MODE=mock|auto|metal`
- `ZYRABIT_TT_MODEL_ID=Qwen/Qwen2.5-3B-Instruct`
- `ZYRABIT_TT_MIN_RAM_GB=24`
- `ZYRABIT_TT_ALLOW_REMOTE_MODEL=false`
- `ZYRABIT_TT_UPSTREAM_URL=http://zyrabit-vllm-tt:8000` (`metal` mode)
- `ZYRABIT_TT_UPSTREAM_MODEL=Qwen/Qwen2.5-3B-Instruct`
- `ZYRABIT_TT_UPSTREAM_API_KEY` (optional)

## Endpoints

- `GET /v1/health`
- `GET /v1/models`
- `POST /v1/chat/completions` (OpenAI, with SSE streaming passthrough)
- `POST /v1/completions` (OpenAI)
- `POST /v1/generate` (legacy)

Chat completions responses include a `zyrabit` block containing `mode`, `source`, `engine`, `arch`, `ttft_ms`, `tps`, and `total_ms`.

## Local Docker

```bash
docker build -t zyrabit-tt-bridge:latest internal/engine/tenstorrent
docker run --rm -p 8090:8090 zyrabit-tt-bridge:latest
```

```bash
curl -fsS http://localhost:8090/v1/health
curl -fsS -X POST http://localhost:8090/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen2.5:3b","messages":[{"role":"user","content":"Hello"}]}'
```

## Docker Compose (Physical Stack)

```bash
docker compose -f zyrabit-slm/docker-compose.yml --profile tenstorrent up --build
```

The `zyrabit-tt-metal` service runs the bridge in `metal` mode against `zyrabit-vllm-tt` (vLLM-TT with `MESH_DEVICE=P150`). Requires 1G hugepages mounted at `/dev/hugepages-1G` and `/dev/tenstorrent` on the host.

## Physical Tenstorrent (Validated on Blackhole p150)

1. **1G Hugepages**: `sudo sysctl -w vm.nr_overcommit_hugepages=64` and mount `none /dev/hugepages-1G hugetlbfs pagesize=1G`.
2. **Engine Image**: `ghcr.io/tenstorrent/tt-inference-server/vllm-tt-metal-src-release-ubuntu-22.04-amd64:0.8.0-55fd115-aa4ae1e`.
3. `docker compose --profile tenstorrent up zyrabit-vllm-tt` and then launch the bridge in `metal` mode against `http://zyrabit-vllm-tt:8000`.

### Physical Stack Findings

- **Model**: `Qwen/Qwen2.5-3B-Instruct`. The 7B variant is **inviable on a single p150** (tt-metal assertion: "Qwen2.5-7B is only supported on 2 or 4 devices", N300/N150x4). `max_model_len=32768` (position embeddings limit).
- **Networking**: `model-network` is `internal: true` (air-gapped) → engine does NOT publish ports to the host; reachable via DNS (`zyrabit-vllm-tt:8000`) from containers on that network. The metal bridge bridges `model-network` + `zyrabit-sovereign-net` so host/API can reach `:8090`.
- **Local API Access**: compose exposes `8080:8080` on `zyrabit-api` and `DOMAIN=localhost` in `.env` (traefik Docker provider broken in this environment: min API 1.40). Without this, `./zyra.sh benchmark` cannot reach the API.
- **Physical Metrics** (p150, Qwen2.5-3B): TTFT ~80-105 ms in steady state, ~20-21 t/s, bridge→engine `total_ms` ~200-400 ms (short response). First inference after cold start incurs compilation (~20 s).
- **Benchmark**: `./zyra.sh benchmark` reports actual bridge TTFT/tps; high total latency (~34 s) stems from RAG pipeline fallback (ChromaDB down, no indexed docs), not inference.
- **F1**: `benchmarks/capture_tt_benchmark.sh` persists JSON metrics in `benchmarks/results/p150-qwen25-3b.json`.
- **F2**: provider `zyrabit-tt` in `~/.config/opencode/opencode.jsonc` points to `http://localhost:8090/v1` (OpenAI-compatible, unauthenticated).
