# Zyrabit SLM

[![CI](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/ci.yml/badge.svg)](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/ci.yml)
[![Security Audit](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/security-audit.yml/badge.svg)](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/security-audit.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/docker--compose-ready-green.svg)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://Zyrabit-tech.github.io/zyrabit-SLM/)

**Sovereign, privacy-first AI assistant with RAG, PII scrubbing, and local inference — fully self-hosted, no cloud required.**

📚 **[Official Documentation](https://Zyrabit-tech.github.io/zyrabit-SLM/)**

---

## What is this?

Zyrabit SLM is a production-grade, local AI stack that lets you run a private LLM assistant against your own documents without sending sensitive data to any external service.

**Problems it solves:**

| Problem | How Zyrabit solves it |
|---|---|
| Data privacy with AI | Heuristic PII scrubbing pipeline before every inference call |
| Vendor lock-in | Pluggable inference adapters (Ollama, OpenAI-compatible, Tenstorrent) |
| RAG complexity | Hybrid BM25 + vector retrieval out of the box |
| Observability gaps | Prometheus metrics + Grafana dashboards included |
| Security blind spots | Zero-trust network topology + Traefik reverse proxy + HMAC-signed webhooks |

---

## What it runs

| Service | Role |
|---|---|
| `traefik` | Local HTTPS ingress, TLS, rate-limiting |
| `api-rag` | FastAPI core — chat, ingest, MCP bridge, webhooks |
| `zyrabit-engine` | Ollama inference engine (native or containerized) |
| `zyrabit-db` | ChromaDB vector store |
| `zyrabit-prometheus` | Metrics scraper |
| `zyrabit-grafana` | Observability dashboard |
| `zyrabit-mcp` | MCP tool server for AI agent integration |
| `zyrabit-n8n` | *(optional)* Automation workflow engine |

**Docker networks:**
- `frontend-network` — public-facing (Traefik only)
- `backend-network` — internal services
- `model-network` — isolated inference network (`internal: true`)

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) + [Docker Compose](https://docs.docker.com/compose/) v2.x
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — Python package manager
- [Ollama](https://ollama.com/download) (native install recommended for GPU/Metal performance)

---

## Quick Start

```bash
# 1. Clone and enter
git clone https://github.com/Zyrabit-tech/zyrabit-SLM.git
cd zyrabit-SLM

# 2. Configure environment
cp zyrabit-slm/example.env zyrabit-slm/.env
# Edit .env with your values (SLM_URL, DB_URL, MODEL_NAME)

# 3. Validate your environment
./zyra-up.sh doctor

# 4. Start the stack and pull base models
./zyra-up.sh install
```

The API will be available at `https://localhost/v1/health` (self-signed cert — use `curl -k`).

---

## Inference: Native Ollama (Recommended)

For best performance on Mac (Metal) or Linux (CUDA), install Ollama natively instead of using the Docker container:

```bash
# macOS: download from https://ollama.com/download/mac
# Linux:
curl -fsSL https://ollama.com/install.sh | sh
```

Then configure `.env`:

```env
# macOS / Windows
INFERENCE_PROVIDER=ollama_host
SLM_URL=http://host.docker.internal:11434/api/generate

# Linux (use your Docker bridge IP)
INFERENCE_PROVIDER=ollama_host
SLM_URL=http://172.17.0.1:11434/api/generate
```

Once configured, you can disable the `zyrabit-engine` service in `docker-compose.yml` to save RAM.

---

## Optional Profiles

Extend the stack with Docker Compose profiles:

```bash
# Automation with n8n
./zyra-up.sh install --profile n8n

# Extended observability (Loki)
docker compose --profile observability-extra up -d

# Local HTTP mode (no TLS, port 8080 direct)
./zyra-up.sh install --local
```

---

## `zyra-up.sh` CLI Reference

```
Usage: ./zyra-up.sh [command] [options]

Commands:
  install          Start the stack and pull required SLM models (default)
  start            Start the stack only (no model pull)
  doctor           Validate environment and print detected runtime profile
  help             Show this message

Options:
  --profile <name>  Start with a Docker Compose profile (n8n, observability-extra)
  --local           Use HTTP mode without TLS (direct port 8080)
  --model <name>    Override the SLM model (e.g., llama3, mistral, qwen2.5:7b)
```

The script auto-detects your hardware:
- **Apple Silicon** → Metal backend, `qwen2.5:7b` default
- **NVIDIA GPU** → CUDA-capable runtime
- **CPU / < 12 GB RAM** → falls back to `qwen2.5:1.5b` (quantized)

---

## Verify Functionality

```bash
# Health check
curl -k https://localhost/v1/health

# Chat (RAG-routed query)
curl -k -X POST https://localhost/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"Explain the Zyrabit architecture"}'

# PII scrubbing demo
python secure_agent.py "My email is john@example.com and SSN is 123-45-6789"

# Ingest a document
curl -k -X POST https://localhost/v1/ingest \
  -F "file=@zyrabit-slm/api-rag/sample_docs/zyrabit_project_overview.txt"

# Observability metrics
curl -k https://localhost/metrics | grep zyrabit_token_usage_total
```

---

## Local Development

```bash
# Install all Python dependencies (uv manages the virtualenv automatically)
uv sync

# Run tests
uv run pytest

# Build and verify all containers
cd zyrabit-slm/scripts
./build_and_verify.sh
```

---

## Local Component URLs

| Component | URL |
|---|---|
| API docs (Swagger) | `https://localhost/docs` |
| Grafana | `https://localhost/grafana` |
| Prometheus | `https://localhost/prometheus` |
| Traefik Dashboard | `https://localhost/dashboard/` |

Use `curl -k` or accept the self-signed cert in your browser.

---

## Repository Structure

```
zyrabit-SLM/
├── zyrabit-slm/              # Docker stack definition
│   ├── api-rag/              # FastAPI backend + security pipeline
│   ├── web-ui/               # Chat frontend (Nginx)
│   ├── mcp/                  # MCP tool server
│   ├── config/               # Prometheus & Grafana provisioning
│   ├── traefik/              # Reverse proxy config & TLS rules
│   └── scripts/              # Dev and verification scripts
├── docs-portal/              # Documentation source (→ GitHub Pages)
├── validation/               # k6 load tests & pentest scripts
├── zyra-up.sh                # Primary CLI entrypoint
├── pyproject.toml            # Unified Python dependency management (uv)
└── secure_agent.py           # CLI demo for PII scrubbing pipeline
```

---

## CI / CD

| Workflow | Trigger | What it does |
|---|---|---|
| `ci.yml` | PR to `beta` / `main` | Contribution policy check → unit tests → production build gate |
| `security-audit.yml` | Weekly + every PR | `pip-audit` dependency vulnerability scan |
| `deploy-docs.yml` | Push to `main` | Publishes `docs-portal/` to GitHub Pages |

**Contribution policy:** all PRs must target `beta` first. Only `beta` can merge to `main`.

---

## Security

- All sensitive data is scrubbed via heuristic regex patterns before any inference call.
- The `model-network` is declared `internal: true` — no external egress from the inference container.
- PII tokens are restored in the final response only, never stored.

See [`SECURITY.md`](SECURITY.md) for the full security policy and vulnerability disclosure process.

---

## Documentation

- 📖 **Full docs:** [https://Zyrabit-tech.github.io/zyrabit-SLM/](https://Zyrabit-tech.github.io/zyrabit-SLM/)
- 🏗️ **Architecture:** [`zyrabit-slm/api-rag/app/HEXAGONAL_ARCHITECTURE.md`](zyrabit-slm/api-rag/app/HEXAGONAL_ARCHITECTURE.md)
- 🤝 **Contributing:** [`CONTRIBUTING_EN.md`](CONTRIBUTING_EN.md)
- 🔒 **Security policy:** [`SECURITY.md`](SECURITY.md)
- 🗂️ **Backend deep-dive:** [`zyrabit-slm/README.md`](zyrabit-slm/README.md)

---

## License

MIT © Zyrabit
