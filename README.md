# Zyrabit SLM

Zyrabit SLM is a local-first sovereign AI stack for regulated environments. It is designed to run on-premise, support air-gapped deployments, and keep sensitive data inside customer-controlled infrastructure.

## What it is

- Local RAG and inference orchestration for private workloads
- FastAPI backend with security-first request handling
- MCP integration for controlled tool access
- SQLite-based state, audit, and memory primitives
- Docker-oriented deployment for isolated environments

## Design Principles

- Data sovereignty first: no dependency on external AI APIs for sensitive data paths
- Air-gapped capable: operate without internet access once dependencies are present
- Hardware-aware: optimized for constrained local clusters
- Auditable by default: explicit flows, visible state, minimal hidden behavior
- Regulated-sector ready: aligned with GDPR, DORA, FedRAMP-style operational constraints

## Repository Layout

- `zyrabit-slm/api-rag/`: main FastAPI application, tests, and domain code
- `mcp/`: MCP server utilities and support scripts
- `internal/`: hardware-specific and experimental integrations
- `validation/`: validation scripts and generated artifacts
- `zyra-up.sh`: primary lifecycle and operator entrypoint

## Architecture

```text
Client -> API Gateway / FastAPI -> Gatekeeper / PII pipeline -> Retriever / RAG
       -> Inference provider -> State tracker / audit store -> Response
```

The stack is intentionally local:

- Requests are sanitized before retrieval or inference
- State is stored in SQLite with WAL mode
- Retrieval can combine keyword and vector search
- Inference can target local Ollama-compatible backends

## Getting Started

### Prerequisites

- Python 3.12.x
- `uv`
- Docker and Docker Compose, if you plan to run the full stack

### Local development

```bash
git clone https://github.com/Zyrabit-tech/zyrabit-SLM.git
cd zyrabit-SLM
uv sync --dev
source .venv/bin/activate
pytest -q zyrabit-slm/api-rag/tests
```

### Run the API

```bash
cd zyrabit-slm/api-rag
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Configuration

Configuration is loaded from environment variables and `.env` files.

Common variables:

- `SLM_URL`: base URL for the local inference service
- `DB_PATH`: path to the SQLite state database
- `MODEL_NAME`: default model identifier
- `DOCS_DIR`: documents directory for ingestion
- `ALLOWED_ORIGINS`: CORS allowlist

## Testing

The main Python test suite lives under `zyrabit-slm/api-rag/tests/`.

Recommended commands:

```bash
pytest -q zyrabit-slm/api-rag/tests
pytest -q zyrabit-slm/api-rag/tests/unit
```

The codebase is intended to run offline. If a test attempts to reach the network, treat that as a bug in the test or implementation.

## Security Notes

- PII should be masked before the model sees the prompt.
- Tool access should be mediated through explicit adapters and policies.
- Secrets must stay on-premise and out of prompts, logs, and exported artifacts.
- Production deployments should define explicit allowlists for origins, tokens, and integrations.

## Operational Notes

- The repo is optimized for local or on-prem deployments, not cloud-only workflows.
- Keep model dependencies and state stores inside the same trust boundary.
- Prefer deterministic behavior, explicit fallbacks, and small surface area changes.

## License

MIT
