# Zyrabit-TT-Bridge

Bridge OpenAI-compatible para inferencia en Tenstorrent Blackhole (p150), con
fallback deterministico (`mock`) para entornos sin hardware.

## Modos

- `ZYRABIT_TT_MODE=mock` (default): responde con el modelo simulado, sin hardware.
- `ZYRABIT_TT_MODE=metal`: proxy hacia un upstream vLLM-TT (imagen
  `tt-inference-server`), midiendo `ttft_ms` real (stream forzado) y calculando
  `tps` contando los tokens streameados (el upstream vLLM-TT 0.8.0 devuelve
  `usage` en ceros; se usa como fallback si no es cero).
- `ZYRABIT_TT_MODE=auto`: detecta GPU via `nvidia-smi` y elige `mock` si no hay.

## Variables

- `ZYRABIT_TT_MODE=mock|auto|metal`
- `ZYRABIT_TT_MODEL_ID=Qwen/Qwen2.5-3B-Instruct`
- `ZYRABIT_TT_MIN_RAM_GB=24`
- `ZYRABIT_TT_ALLOW_REMOTE_MODEL=false`
- `ZYRABIT_TT_UPSTREAM_URL=http://zyrabit-vllm-tt:8000` (modo `metal`)
- `ZYRABIT_TT_UPSTREAM_MODEL=Qwen/Qwen2.5-3B-Instruct`
- `ZYRABIT_TT_UPSTREAM_API_KEY` (opcional)

## Endpoints

- `GET /v1/health`
- `GET /v1/models`
- `POST /v1/chat/completions` (OpenAI, con SSE streaming passthrough)
- `POST /v1/completions` (OpenAI)
- `POST /v1/generate` (legacy)

Las respuestas de chat/completions incluyen el bloque `zyrabit` con
`mode`, `source`, `engine`, `arch`, `ttft_ms`, `tps` y `total_ms`.

## Docker local

```bash
docker build -t zyrabit-tt-bridge:latest internal/engine/tenstorrent
docker run --rm -p 8090:8090 zyrabit-tt-bridge:latest
```

```bash
curl -fsS http://localhost:8090/v1/health
curl -fsS -X POST http://localhost:8090/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen2.5:3b","messages":[{"role":"user","content":"Hola"}]}'
```

## Docker Compose (stack real)

```bash
docker compose -f zyrabit-slm/docker-compose.yml --profile tenstorrent up --build
```

El servicio `zyrabit-tt-metal` corre el bridge en modo `metal` contra
`zyrabit-vllm-tt` (vLLM-TT con `MESH_DEVICE=P150`). Requiere hugepages 1G
montados en `/dev/hugepages-1G` y `/dev/tenstorrent` en el host.

## Tenstorrent real (validado en Blackhole p150)

1. Hugepages 1G: `sudo sysctl -w vm.nr_overcommit_hugepages=64` y mount
   `none /dev/hugepages-1G hugetlbfs pagesize=1G`.
2. Imagen del motor: `ghcr.io/tenstorrent/tt-inference-server/vllm-tt-metal-src-release-ubuntu-22.04-amd64:0.8.0-55fd115-aa4ae1e`.
3. `docker compose --profile tenstorrent up zyrabit-vllm-tt` y luego el bridge
   en modo `metal` contra `http://zyrabit-vllm-tt:8000`.

### Hallazgos del stack real

- **Modelo**: `Qwen/Qwen2.5-3B-Instruct`. El 7B es **inviable en p150 single**:
  assertion de tt-metal ("Qwen2.5-7B is only supported on 2 or 4 devices",
  N300/N150x4). `max_model_len=32768` (límite de position embeddings).
- **Redes**: `model-network` es `internal: true` (air-gap) → el engine NO publica
  puertos al host; es alcanzable por DNS (`zyrabit-vllm-tt:8000`) desde
  contenedores de esa red. El bridge metal está en `model-network` +
  `zyrabit-sovereign-net` para que el host/API alcancen `:8090`.
- **Acceso local al API**: el compose expone `8080:8080` en `zyrabit-api` y
  `DOMAIN=localhost` en `.env` (el provider Docker de traefik está roto en este
  entorno: min API 1.40). Sin esto, `./zyra.sh benchmark` no llega al API.
- **Métricas reales** (p150, Qwen2.5-3B): TTFT ~80-105 ms en estado estable,
  ~20-21 t/s, `total_ms` bridge→engine ~200-400 ms (respuesta corta). La primera
  inferencia tras arrancar el engine paga la compilación (~20 s).
- **Benchmark**: `./zyra.sh benchmark` reporta TTFT/tps reales del bridge; la
  latencia total alta (~34 s) es del pipeline RAG (ChromaDB caída, sin docs
  indexados), no de la inferencia.
- **F1**: `benchmarks/capture_tt_benchmark.sh` guarda el JSON con métricas reales
  en `benchmarks/results/p150-qwen25-3b.json`.
- **F2**: provider `zyrabit-tt` en `~/.config/opencode/opencode.jsonc` apunta a
  `http://localhost:8090/v1` (OpenAI-compatible, sin auth).
