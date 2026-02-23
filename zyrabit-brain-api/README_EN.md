# Zyrabit Brain API

[Main README](README.md)

Backend stack for secure local RAG, MCP bridge, and observability.

## What this folder contains

- `api-rag/`: FastAPI service and security pipeline.
- `docker-compose.yml`: local orchestration with segmented networks.
- `config/`: Prometheus/Grafana provisioning.
- `traefik/`: reverse-proxy dynamic security config.

## Core capabilities

- Interceptor-based PII anonymization before SLM inference.
- Reversible token de-anonymization after response generation.
- Prometheus metrics at `/metrics`:
  - `zyrabit_token_latency_ms_per_token`
  - `zyrabit_token_usage_total`
  - `zyrabit_security_hits_total`
- MCP endpoints:
  - `GET /mcp/config.json`
  - `POST /mcp`

## Quick start

From repository root:

```bash
chmod +x zyra-up.sh
./zyra-up.sh install
```

Setup script roles from repository root:

- `install.sh`: bootstrap wrapper for first-time setup.
- `zyra-up.sh`: primary setup and lifecycle entrypoint.

Or from this folder:

```bash
docker compose up -d
```

## Service topology

- `traefik`: ingress, TLS redirect, rate-limiting.
- `api-rag`: FastAPI core.
- `slm-engine`: Ollama inference engine.
- `vector-db`: ChromaDB persistence layer.
- `prometheus` + `grafana`: local monitoring.
- `loki` (optional profile): extended logs.
- `docs-portal` (optional profile): local docs container.

Networks:

- `frontend-network`
- `backend-network`
- `model-network` (`internal: true`)

## Testing

```bash
cd api-rag
python3 -m pytest -q
```

Focus suites:

- `tests/test_security.py`: critical PII and pipeline behavior.
- `tests/test_services_security.py`: no raw PII reaches model payload.
- `tests/test_integration.py`: API integration.
- `tests/test_mcp.py`: MCP interface and sanitization behavior.

## Security references

- Repository-wide security policy: `../SECURITY.md`
- MCP static config: `../mcp/config.json`
