# Zyrabit SLM — Backend Stack

Backend stack for secure local RAG, MCP bridge, and full-stack observability.

> **Recommended Python runtime: 3.12.** Avoid 3.13+ until all dependencies declare support.

---

## What this folder contains

| Path | Purpose |
|---|---|
| `api-rag/` | FastAPI service, security pipeline, RAG engine |
| `docker-compose.yml` | Production stack with Traefik, segmented networks |
| `docker-compose.local.yml` | Local override — direct HTTP port 8080, no TLS |
| `config/` | Prometheus & Grafana provisioning files |
| `traefik/` | Reverse proxy dynamic config, TLS rules, rate-limiting |
| `scripts/` | Dev, build, and verification scripts |
| `prompts/` | Editable system prompts for the SLM |
| `secrets/` | Docker secrets (never commit real values) |

---

## Core capabilities

- **PII scrubbing:** Interceptor pipeline anonymizes sensitive entities (email, phone, SSN, credit cards, names, amounts) before every inference call using heuristic regex + Luhn validation.
- **Reversible de-anonymization:** Tokens (`<USER_EMAIL_1>`, `<SSN_1>`, etc.) are restored in the final response. Raw data never touches the model.
- **Hybrid RAG retrieval:** BM25 keyword matching + ChromaDB vector search for deterministic, high-recall retrieval.
- **Pluggable inference:** Swap between `ollama`, `ollama_host`, `ollama_docker`, or any `openai_compatible` endpoint via a single env variable.
- **MCP bridge:** Exposes Zyrabit tools (`secure_chat`, `sanitize_text`) through the Model Context Protocol for AI agent integration.
- **Observability:** Prometheus metrics + Grafana dashboards included. Zero public ports — everything served through Traefik.

---

## Environment Setup

### Required variables

Copy the template and fill in your values:

```bash
cp example.env .env
```

| Variable | Description |
|---|---|
| `SLM_URL` | Ollama inference endpoint |
| `DB_URL` | ChromaDB endpoint |
| `MODEL_NAME` | SLM model to use (e.g. `qwen2.5:7b`) |
| `INFERENCE_PROVIDER` | Adapter name: `ollama`, `ollama_host`, `openai_compatible` |
| `INFERENCE_TIMEOUT_SECONDS` | Max seconds to wait for a model response |
| `PROMETHEUS_BASIC_AUTH` | `user:htpasswd_hash` for Prometheus basic auth |
| `GRAFANA_BASIC_AUTH` | `user:htpasswd_hash` for Grafana basic auth |

Generate a bcrypt hash for basic auth:

```bash
htpasswd -nbB admin 'your-password'
```

### Inference providers

```env
# Ollama running inside Docker (default)
INFERENCE_PROVIDER=ollama
SLM_URL=http://zyrabit-engine:11434/api/generate

# Native Ollama on the host (Mac/Windows — best performance)
INFERENCE_PROVIDER=ollama_host
SLM_URL=http://host.docker.internal:11434/api/generate

# OpenAI-compatible endpoint (e.g. LiteLLM, vLLM, BitNet)
INFERENCE_PROVIDER=openai_compatible
INFERENCE_BASE_URL=http://your-endpoint/v1/chat/completions
```

### n8n integration variables

```env
N8N_SERVICE_TOKEN=replace-with-strong-token
N8N_WEBHOOK_SIGNING_SECRET=replace-with-hmac-secret
N8N_REQUIRE_SIGNATURE=true

# Production: use file-based secrets, never plain values in compose files
N8N_SERVICE_TOKEN_FILE=/run/secrets/n8n_service_token
N8N_WEBHOOK_SIGNING_SECRET_FILE=/run/secrets/n8n_webhook_signing_secret
```

---

## Starting the Stack

```bash
# From the repository root — preferred
./zyra-up.sh install          # Start + pull models
./zyra-up.sh start            # Start only
./zyra-up.sh doctor           # Validate environment

# Manually from this directory
docker compose up -d

# Local HTTP mode (no TLS, port 8080)
docker compose -f docker-compose.local.yml up -d
```

### Adding optional profiles

```bash
# n8n automation engine
./zyra-up.sh install --profile n8n

# Extended observability (Loki log aggregation)
docker compose --profile observability-extra up -d
```

---

## Service Topology

```
                     ┌─────────────────────────────────────────┐
                     │         frontend-network (bridge)        │
                     └──────────────┬──────────────────────────┘
                            Traefik │ (TLS, rate-limit, auth)
                     ┌─────────────▼──────────────────────────┐
                     │          backend-network (bridge)       │
                     │  api-rag   chroma-db   prometheus       │
                     │  grafana   mcp         n8n (optional)   │
                     └──────────────┬─────────────────────────┘
                                    │
                     ┌──────────────▼─────────────────────────┐
                     │   model-network (internal: true)        │
                     │   zyrabit-engine (Ollama)               │
                     └────────────────────────────────────────┘
```

| Service | Published path |
|---|---|
| `api-rag` | `https://localhost/v1/*`, `https://localhost/socket.io` |
| `grafana` | `https://localhost/grafana` |
| `prometheus` | `https://localhost/prometheus` |
| `n8n` *(optional)* | `https://localhost/n8n` |

---

## API Reference

### Health

```bash
curl -k https://localhost/v1/health
# → {"status":"ok","slm":"online","db":"online"}
```

### Chat

```bash
curl -k -X POST https://localhost/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "Explain the Zyrabit architecture"}'
```

```json
{
  "response": "...",
  "metadata": {
    "decision": "search_rag_database",
    "rag_hits": 2,
    "latency_ms": 305.44
  }
}
```

### Ingest a document

```bash
curl -k -X POST https://localhost/v1/ingest \
  -F "file=@api-rag/sample_docs/zyrabit_project_overview.txt"
```

```json
{
  "status": "success",
  "filename": "zyrabit_project_overview.txt",
  "chunks_processed": 4,
  "ingest_id": "abc123"
}
```

### n8n webhook

```bash
curl -k https://localhost/v1/integrations/n8n/webhook \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${N8N_SERVICE_TOKEN}" \
  -H "X-Zyrabit-Signature: sha256=<hmac_sha256_of_body>" \
  -d '{"text":"Summarize observability status","workflow_id":"wf-001","execution_id":"exec-001"}'
```

See [`docs/CURL_EXAMPLES.md`](docs/CURL_EXAMPLES.md) for the full reference.

---

## Architecture

Zyrabit follows a **Hexagonal (Ports & Adapters)** architecture inside `api-rag/`:

| Layer | Responsibility |
|---|---|
| **Edge / Ingress** | Traefik — TLS, rate-limiting, auth middleware |
| **Transport** | FastAPI routers — HTTP endpoints, request parsing |
| **Security Pipeline** | PII anonymization interceptors — runs before domain logic |
| **Domain** | Use cases, Gatekeeper router, RAG orchestration |
| **Ports** | Contracts for inference, vector store, automation |
| **Adapters** | Ollama, ChromaDB, n8n, MCP implementations |
| **Observability** | Prometheus, Grafana, optional Loki |

See [`api-rag/app/HEXAGONAL_ARCHITECTURE.md`](api-rag/app/HEXAGONAL_ARCHITECTURE.md) for the full guide.

---

## Development

```bash
# Install all Python dependencies
uv sync

# Run the test suite
uv run pytest

# Build and verify all containers locally
cd scripts
./build_and_verify.sh          # local mode (HTTP, port 8080)
./build_and_verify.sh --prod   # production mode (Traefik + HTTPS)
```

### Test suites

| Suite | What it covers |
|---|---|
| `tests/test_security.py` | PII sanitization, anonymize/de-anonymize roundtrip |
| `tests/test_pii_pipeline.py` | Luhn validation, shard building, entity deduplication |
| `tests/test_services_security.py` | PII must never reach the model payload |
| `tests/test_integration.py` | Full API flow with mocked infrastructure |
| `tests/test_integration_critical.py` | Gatekeeper routing logic (no mocks) |
| `tests/test_mcp.py` | MCP protocol contract and sanitization |

---

## Adding a new inference adapter

1. Implement the `InferencePort` interface in `api-rag/app/adapters/`.
2. Register it in `api-rag/app/inference_factory.py`.
3. Set `INFERENCE_PROVIDER=your_adapter_name` in `.env`.

A blueprint is available at [`api-rag/app/adapters/make_adapter_blueprint.py`](api-rag/app/adapters/make_adapter_blueprint.py).

---

## Security

- `model-network` is declared `internal: true` — the inference engine has no egress.
- PII tokens are resolved only in the final response layer, never persisted.
- Production secrets must use `_FILE` variables with Docker Secrets or an on-prem Vault.
- All external adapters require `Authorization: Bearer` + optional HMAC signature validation.

Full policy: [`../SECURITY.md`](../SECURITY.md)

---

## Documentation

- 📖 Full docs: [https://Zyrabit-tech.github.io/zyrabit-SLM/](https://Zyrabit-tech.github.io/zyrabit-SLM/)
- 🏗️ Architecture: [`api-rag/app/HEXAGONAL_ARCHITECTURE.md`](api-rag/app/HEXAGONAL_ARCHITECTURE.md)
- 🤝 Contributing: [`../CONTRIBUTING_EN.md`](../CONTRIBUTING_EN.md)
- 🔒 Security: [`../SECURITY.md`](../SECURITY.md)
