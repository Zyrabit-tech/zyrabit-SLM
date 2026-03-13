# Zyrabit Brain API

[Main README](README.md)

Backend stack for secure local RAG, MCP bridge, and observability.

> Recommended local runtime: **Python 3.12** to avoid incompatibilities with legacy dependencies on Python 3.14+.

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
- n8n integration endpoint (adapter + policies):
  - `POST /v1/integrations/n8n/webhook`

## Quick start

From repository root:

```bash
chmod +x zyra-up.sh
./zyra-up.sh install
```

Setup script roles from repository root:

- `install.sh`: bootstrap wrapper for first-time setup.
- `zyra-up.sh`: primary setup and lifecycle entrypoint.

## Environment variable validation

The `zyra-up.sh` script validates effective variable values before starting:

- Prioritizes runtime environment variables (e.g. CI/CD or systemd).
- Falls back to `zyrabit-brain-api/.env` if not found at runtime.
- Must exist and have a valid value:
  - `SLM_URL`
  - `DB_URL`
  - `MODEL_NAME`
- Empty or invalid values like `undefined`, `null`, `none` are rejected.

Full template: copy `example.env` to `.env` and adjust values:

```bash
cp example.env .env
```

Minimal `.env` example (optional if variables are already exported on your server):

```bash
INFERENCE_PROVIDER=ollama
SLM_URL=http://slm-engine:11434/api/generate
DB_URL=http://vector-db:8000
MODEL_NAME=qwen2.5:7b
INFERENCE_TIMEOUT_SECONDS=120
PROMETHEUS_BASIC_AUTH=admin:$2y$05$...   # htpasswd -nbB admin 'password'
GRAFANA_BASIC_AUTH=admin:$2y$05$...      # idem
```

### Pluggable inference providers (factory + adapters)

The inference layer uses a contract-based port (`app/ports/inference_port.py`) with a factory (`app/inference_factory.py`) and adapters:

- `ollama` / `ollama_host` / `ollama_docker` -> `SLM_URL=/api/generate`
- `openai_compatible` -> `INFERENCE_BASE_URL=/v1/chat/completions`

Hybrid mode example (native host Ollama + rest in Docker):

```bash
INFERENCE_PROVIDER=ollama_host
SLM_URL=http://host.docker.internal:11434/api/generate
MODEL_NAME=qwen2.5:7b
```

n8n integration variables (adapter webhook):

```bash
N8N_SERVICE_TOKEN=replace-with-strong-token
N8N_WEBHOOK_SIGNING_SECRET=replace-with-hmac-secret
N8N_REQUIRE_SIGNATURE=true
```

In production, use file-based secrets or Vault (never hardcode):

```bash
N8N_SERVICE_TOKEN_FILE=/run/secrets/n8n_service_token
N8N_WEBHOOK_SIGNING_SECRET_FILE=/run/secrets/n8n_webhook_signing_secret
```

Basic-auth credentials for observability routes in Traefik:

```bash
PROMETHEUS_BASIC_AUTH=<user:htpasswd_hash>
GRAFANA_BASIC_AUTH=<user:htpasswd_hash>
```

Hash generation example:

```bash
htpasswd -nbB admin 'change-this'
```

## Usage examples

Verify environment and configuration:

```bash
./zyra-up.sh doctor
```

Start infrastructure:

```bash
./zyra-up.sh start
```

Start stack manually with Docker Compose:

```bash
cd zyrabit-brain-api
docker compose up -d
```

Start and install base models:

```bash
./zyra-up.sh install
```

Pull models manually (without automatic installer flow):

```bash
docker compose exec -T slm-engine ollama pull qwen2.5:7b
docker compose exec -T slm-engine ollama pull mxbai-embed-large
```

Check API health:

```bash
curl -k https://localhost/health
```

Send a query to the router:

```bash
curl -k https://localhost/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"Explain the Zyrabit architecture"}'
```

`POST /v1/chat` response:

```json
{
  "response": "...",
  "metadata": {
    "route_decision": "search_rag_database",
    "rag_hits": 2,
    "latency_ms": 305.44
  }
}
```

Ingest a document:

```bash
curl -k -X POST https://localhost/v1/ingest \
  -F "file=@api-rag/sample_docs/zyrabit_project_overview.txt"
```

`POST /v1/ingest` response:

```json
{
  "status": "success",
  "filename": "zyrabit_project_overview.txt",
  "chunks_processed": 4,
  "message": "Documento ingestado correctamente en la base de conocimiento.",
  "ingest_id": "..."
}
```

See full examples: `docs/CURL_EXAMPLES.md` and n8n workflow in `docs/n8n_zyrabit_webhook_workflow.json`.

Send an event from n8n to the adapter:

```bash
curl -k https://localhost/v1/integrations/n8n/webhook \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${N8N_SERVICE_TOKEN}" \
  -H "X-Zyrabit-Signature: sha256=<hmac_sha256_of_body>" \
  -d '{"text":"Summarize observability status","workflow_id":"wf-001","execution_id":"exec-001"}'
```

## Abstraction layers

The solution is organized by layers to separate responsibilities:

1. **Edge/Ingress layer**
   - `traefik` receives traffic and applies TLS, redirects, and rate limiting.
2. **Application layer**
   - `api-rag` exposes HTTP endpoints and coordinates business logic.
3. **Security layer**
   - Anonymization/de-anonymization pipeline for sensitive data.
4. **Inference layer**
   - `slm-engine` (Ollama) runs the local model.
5. **Knowledge layer**
   - `vector-db` stores and retrieves embeddings/context.
6. **Observability layer**
   - `prometheus`, `grafana`, and optionally `loki`.

## Applied patterns

- **Interceptor Pipeline**: chain of transformations to sanitize input/output.
- **Router Pattern**: the `/v1/chat` endpoint decides between RAG flow or direct response.
- **Facade/API Gateway**: FastAPI and Traefik simplify access to the distributed system.
- **Defense in Depth**: segmented networks + sanitization + reverse proxy.

## Architecture

- **Service-oriented architecture (local micro-services)** orchestrated with Docker Compose.
- **Clean / Layered style** inside `api-rag` to isolate transport, services, and security.
- **Local Zero-Trust topology**: no sensitive data leaves the infrastructure.

## Service topology

- `traefik`: ingress, TLS redirect, rate-limiting.
- `api-rag`: FastAPI core.
- `slm-engine`: Ollama inference engine.
- `vector-db`: ChromaDB persistence layer.
- `prometheus` + `grafana`: local monitoring.
- `loki` (optional profile): extended logs.
- `docs-portal` (optional profile): local docs container.
- `n8n` (optional `automation` profile): automation workflow engine published through Traefik (`/n8n`).

Networks:

- `frontend-network`
- `backend-network`
- `model-network` (`internal: true`)

## Integration policies (n8n and future adapters)

- **Single entrypoint**: all public traffic goes through Traefik (`https://localhost`), no extra public service ports.
- **Service token**: `Authorization: Bearer <token>` required for automation adapters.
- **Webhook integrity**: HMAC SHA-256 signature in `X-Zyrabit-Signature` when `N8N_REQUIRE_SIGNATURE=true`.
- **Stable contract**: minimum payload `{ "text": "..." }`; optional metadata `workflow_id`, `execution_id`.
- **Hexagonal boundary**: every new external tool (Make, Strapi, DB connectors) should add a dedicated adapter over a port, without coupling core domain logic to provider APIs.
- **Production secrets**: use `_FILE` variables with Docker Secrets or on-prem Vault, never plain secrets in `docker-compose.yml`.

## Observability without public ports

- `grafana` is published at `https://localhost/grafana`.
- `prometheus` is published at `https://localhost/prometheus`.
- Both are behind Traefik and protected with `basicauth` middleware.

## Template for new adapters (Make)

A reusable template is included at:

- `api-rag/app/adapters/make_adapter_blueprint.py`

It demonstrates:

- bearer-token validation
- HMAC signature validation
- external payload normalization into a stable internal contract

## Next step: feedback-driven local re-training

Recommended evolution path for a local super-fine-tuning pipeline:

1. Emit a `model_miss_detected` event from `automation_port`.
2. Persist curated examples in a local feedback dataset.
3. Trigger controlled offline fine-tuning jobs (LoRA/PEFT).
4. Version and promote tuned models through automated evaluation gates.

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
