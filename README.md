<div align="center">

<img src="https://assets.zyrabit.com/logo_zyrabit.png" alt="Zyrabit SLM" width="120" />

# Zyrabit SLM

**Sovereign AI infrastructure for regulated environments.**
Run language models entirely on your infrastructure — no external APIs, no data leakage, full audit trail.

[![CI](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/ci.yml/badge.svg)](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/ci.yml)
[![Security](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/security.yml/badge.svg)](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/security.yml)
[![Version](https://img.shields.io/badge/v2.2.3-Sovereign-3f5a6d?style=flat-square&labelColor=e2ecf4)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-6090b4?style=flat-square)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white&style=flat-square)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&style=flat-square)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white&style=flat-square)](https://docs.docker.com/compose/)
[![Ollama](https://img.shields.io/badge/Ollama-compatible-3f5a6d?style=flat-square)](https://ollama.com)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-6090b4?style=flat-square)](CONTRIBUTING.md)

[Quickstart](#-quickstart) · [Architecture](#-architecture) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

</div>

---

## What Zyrabit SLM actually is

Zyrabit SLM is a **local-first AI runtime** built for teams that cannot send data to the cloud — healthcare, finance, legal, government, and defense. It gives you:

- A **FastAPI inference API** with PII masking before the model ever sees a prompt
- **RAG (Retrieval-Augmented Generation)** over your own documents, combining keyword and vector search
- **MCP (Model Context Protocol)** for controlled, auditable tool access — the model only accesses what you explicitly allow
- **SQLite state store** in WAL mode for session memory, audit logs, and conversation history
- **Grafana + Prometheus observability** stack — latency, throughput, model health in real time
- **Traefik reverse proxy** with routing and TLS termination for production on-prem deployments
- **Air-gap capable**: once dependencies are present, zero internet access required

> Think of it as your own private ChatGPT backend — minus the telemetry, plus compliance.

---

## 🏗 Architecture

```text
                    Client Request
                         │
                         ▼
               ┌─────────────────┐
               │   API Gateway   │  FastAPI + Traefik (TLS)
               │  Rate limiting  │
               └────────┬────────┘
                         │
                    ┌────▼────┐
                    │Gatekeeper│  PII detection, prompt sanitization, policy enforcement
                    └────┬────┘
                         │
                  ┌──────┴──────┐
                  │             │
             ┌────▼───┐   ┌────▼────┐
             │  RAG   │   │  State  │  SQLite WAL — session memory, audit log
             │ Engine │   │  Store  │
             └────┬───┘   └─────────┘
                  │
        ┌─────────▼──────────┐
        │  Inference Layer   │  Ollama-compatible local backends (Mistral, Phi-3, Llama-3, etc.)
        └────────────────────┘
                  │
             ┌────▼────┐
             │ Response │  Auditable, stateful, no external calls
             └─────────┘
```

All traffic is local. State never leaves your trust boundary.

---

## ⚡ Quickstart

**Prerequisites:** Python 3.12, [uv](https://github.com/astral-sh/uv), Docker & Docker Compose, [Ollama](https://ollama.com) running locally

```bash
# 1. Clone and install
git clone https://github.com/Zyrabit-tech/zyrabit-SLM.git
cd zyrabit-SLM
uv sync --dev
source .venv/bin/activate

# 2. Start in local/dev mode (default — no flags needed)
./zyra.sh install

# 3. Test it
curl -X POST http://localhost:8082/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer zyrabit-local-token" \
  -d '{"text": "Summarize our Q3 compliance report"}'
```

> **First time?** Run `./zyra.sh wizard` for an interactive setup covering model selection, inference engine, database, and audio transcription.

> **Going to production?** Run `./zyra.sh install --production` — triggers the domain, HTTPS, and PostgreSQL configuration wizard.

---

## 🔍 Real-world use cases

| Scenario | What Zyrabit SLM does |
|---|---|
| **Legal firm** asks AI to review contracts | Documents stay on firm servers; PII masked before inference |
| **Hospital** needs RAG over patient records | Air-gapped, HIPAA-aligned; no record ever leaves the datacenter |
| **Bank** runs internal compliance Q&A | Audit log of every query, model response, and retrieved chunk |
| **Government agency** deploys on classified infra | Fully offline after initial setup; Ollama + local model weights |
| **Enterprise IT** builds internal knowledge bot | Grafana dashboard shows latency, model load, and query volume |

---

## 📦 Stack components

```text
zyrabit-slm/
├── api-rag/              # FastAPI app — inference, RAG, PII pipeline, audit
├── config/               # Environment-specific configuration
├── prompts/              # Versioned system prompts (auditable artifacts)
├── web-ui/               # Browser interface for local interaction
├── grafana/              # Dashboards — latency, throughput, model health
├── prometheus/           # Metrics collection and alerting rules
├── traefik/              # Reverse proxy, TLS, routing (production only)
├── scripts/              # Operational helpers
├── docker-compose.yml    # Production stack
└── docker-compose.local.yml  # Local/Dev stack (default)
mcp/                      # Model Context Protocol server (controlled tool access)
internal/                 # Hardware-specific integrations (edge/constrained clusters)
validation/               # Validation scripts and compliance artifacts
zyra.sh                   # Unified CLI: install · start · stop · wizard · benchmark
zyra-up.sh                # Legacy shim → delegates to zyra.sh
```

---

## 🧪 Testing

```bash
# All unit tests
pytest -q zyrabit-slm/api-rag/tests

# Unit tests only (offline, no network)
pytest -q zyrabit-slm/api-rag/tests/unit

# Sovereign QA validation (PII + architecture + air-gap)
./zyra.sh validate --e2e-security
```

> **Rule**: if a test reaches the network, it's a bug. The entire test suite runs offline.

---

## 🎯 Challenges & Community Contributions

We grow through community challenges. Pick one and open a PR:

### 🟢 Good First Issues

- [ ] **Add a new PII pattern** — extend the masking pipeline to detect CURP (Mexico) or NHS numbers (UK)
- [ ] **Write a new Grafana panel** — visualize average tokens per query over time
- [ ] **Add a model switcher endpoint** — `POST /model` to hot-swap the inference target without restart

### 🟡 Intermediate

- [ ] **Build a document connector** — ingest from Notion, Google Drive, or SharePoint into the RAG store
- [ ] **Implement session expiry** — auto-purge SQLite sessions older than N days via cron or background task
- [ ] **Add RBAC to the API** — role-based access where different API keys get different tool permissions

### 🔴 Advanced

- [ ] **MCP adapter for a new tool** — implement a sandboxed SQL query tool with explicit allow/deny policies
- [ ] **Benchmark harness** — measure RAG retrieval quality vs. chunk size and embedding model across 3+ models
- [ ] **Edge deployment guide** — document and test running the stack on a Raspberry Pi 5 or Jetson Orin Nano

---

## 🛡 Security Model

- **PII masking** runs before the prompt reaches the model — the model never sees raw sensitive data
- **Tool access** via MCP requires explicit adapter registration — no implicit function calling
- **Secrets** stay on-premise: never in prompts, logs, or exported artifacts
- **Production deployments** must define explicit allowlists for origins, tokens, and integrations
- See [SECURITY.md](SECURITY.md) for vulnerability reporting

---

## 📋 Compliance alignment

| Standard | Relevant capability |
|---|---|
| **GDPR** | PII masking, data residency, right-to-erasure via session purge |
| **DORA** | Audit log, deterministic fallbacks, explicit state |
| **HIPAA** | Air-gap capable, no PHI leaves infrastructure |
| **FedRAMP** | On-prem deployment, no third-party API dependencies |
| **ISO 27001** | Access control via RBAC (roadmap), audit trail |

---

## 🤝 Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR. The short version:

1. Fork → branch from `main` → PR with tests
2. No network calls in tests — treat them as bugs
3. Prefer small, auditable changes over large refactors

---

## License

MIT © [Zyrabit](https://zyrabit.com)
