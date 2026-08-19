<div align="center">

<img src="https://assets.zyrabit.com/logo_zyrabit.png" alt="Zyrabit SLM" width="120" />

# Zyrabit SLM

**Local-first AI runtime for evaluating sovereign document retrieval & inference workflows.**

[![CI](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/ci.yml/badge.svg)](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/ci.yml)
[![Security](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/security.yml/badge.svg)](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/security.yml)
[![Version](https://img.shields.io/badge/v3.0.0--rc.1-Beta-3f5a6d?style=flat-square&labelColor=e2ecf4)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-6090b4?style=flat-square)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white&style=flat-square)](https://python.org)

[Quickstart](#-quickstart) · [Architecture](#-architecture) · [Capability Matrix](#-capability-matrix) · [Security](SECURITY.md)

</div>

---

## 📌 Scope & Status Notice

Zyrabit SLM is a **beta local-first runtime** for teams evaluating private document retrieval and language-model workflows. It can run on customer-controlled infrastructure and supports an offline deployment profile (`docker-compose.airgapped.yml`) after images, model weights, and dependencies are prepared locally.

> **Notice**: It is not a compliance certification (GDPR/HIPAA/ISO), a guarantee against data exposure, or a substitute for an organization's security review. Review the threat model and deployment guide before using sensitive production data.

---

## 📊 Capability Matrix

| Capability | Status | Evidence / Verification | Limitations |
| --- | --- | --- | --- |
| **Inference Engine** | `Beta` | FastAPI + Ollama API integration test | Performance dependent on host GPU/RAM |
| **Document Retrieval (RAG)** | `Beta` | Hybrid search & Chroma DB unit tests | Single-node SQLite / Chroma state |
| **PII Sanitization** | `Beta` | Regex & Luhn algorithm test suite | May miss novel formats/multilingual PII |
| **Air-gapped Execution** | `Validated` | `docker-compose.airgapped.yml` isolated network | Weights must be pre-loaded locally |
| **Enterprise RBAC** | `Roadmap` | Planned for v3.1 | Currently single-tenant / basic auth |

---

## What Zyrabit SLM offers

- **FastAPI inference API** with PII sanitization controls before prompt processing
- **RAG (Retrieval-Augmented Generation)** over local documents
- **MCP (Model Context Protocol)** for controlled tool access
- **Air-gap capable profile**: zero public DNS / egress dependencies when using `docker-compose.airgapped.yml`
- **Grafana + Prometheus observability** stack

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

**Prerequisites:** Python 3.12, [uv](https://github.com/astral-sh/uv), Docker & Docker Compose, [Ollama](https://ollama.com) (or local GGUF weights)

```bash
# 1. Clone and install
git clone https://github.com/Zyrabit-tech/zyrabit-SLM.git
cd zyrabit-SLM
chmod +x zyra.sh install.sh
uv sync --all-groups
source .venv/bin/activate

# 2. Start in local/dev mode (default — direct open ports, no Traefik)
./zyra.sh install

# 3. Test local inference
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer zyrabit-local-token" \
  -d '{"text": "Summarize our sovereign architecture capabilities"}'
```

> [!TIP]
> **Avoid using `sudo ./zyra.sh`**: Running scripts with `sudo` creates root-owned files that break normal user permissions. If you see Docker `permission denied` errors, add your user to the docker group: `sudo usermod -aG docker $USER && newgrp docker`.

> **Local / Dev Mode (Default)**: Runs FastAPI, Web UI, Chroma Vector DB, Grafana (:3000), and Prometheus (:9090) with direct open ports and auto-discovered local models. No TLS or reverse proxy complexity.
>
> **Production Mode**: Pass `./zyra.sh install --production` or `./zyra.sh start --production` to activate Traefik TLS reverse proxy, strict `.env` credential validation, domain binding, and production hardening.

---

## 🤖 AI Agent Setup (Cursor, Antigravity, Windsurf, Cline)

If you are using an AI coding assistant to configure, troubleshoot, or build tools on Zyrabit SLM, copy and paste the prompt below into your assistant's chat or system instructions.

### 📋 Setup & Autonomous Troubleshooting Prompt

```text
You are pair-programming on Zyrabit SLM, a sovereign, local-first AI runtime.

Task: Setup, verify, and operate the local Zyrabit SLM environment.

1. Environment & Permissions Check:
   - Check if Docker daemon is running and user has docker permissions (no root/sudo needed).
   - Ensure scripts have executable permissions: `chmod +x zyra.sh install.sh`
   - Run `python3 --version` (requires Python 3.12) and check if `uv` is installed.
   - Check if Ollama is running locally: `curl -s http://localhost:11434/api/tags` or if local GGUF models exist.

2. Installation & Configuration:
   - Run `uv sync --all-groups` to synchronize the virtual environment.
   - Run `./zyra.sh install` (or `./zyra.sh start` if already configured).
   - Local models in Ollama, HF cache, or ~/models will be auto-detected.

3. Health & Sanity Checks:
   - Check container status: `docker compose -f zyrabit-slm/docker-compose.yml ps`
   - Test health endpoint: `curl -s http://localhost:8080/v1/health`
   - Test local inference:
     curl -X POST http://localhost:8080/v1/chat \
       -H "Content-Type: application/json" \
       -H "Authorization: Bearer zyrabit-local-token" \
       -d '{"text": "Hello, Zyrabit!"}'

4. Architectural Invariants:
   - Zero external egress: All models, embeddings, and vector stores must run locally.
   - PII Sandwich: Prompts are sanitized before reaching inference engines.
   - Tool calling must be routed through the local MCP gateway.
```

### 🧩 MCP Server Configuration for Agents

Connect this Zyrabit instance as a local MCP server for your agent (`claude_desktop_config.json`, Cursor MCP, or Antigravity MCP):

```json
{
  "zyrabit-slm": {
    "command": "uv",
    "args": [
      "--directory",
      "/path/to/zyrabit-SLM/mcp",
      "run",
      "zyrabit-mcp"
    ],
    "env": {
      "ZYRABIT_API_URL": "http://localhost:8080",
      "ZYRABIT_API_KEY": "zyrabit-local-token"
    }
  }
}
```

---

## 🔍 Real-world use cases

| Scenario | What Zyrabit SLM does |
|---|---|
| **Legal firm** asks AI to review contracts | Documents stay on firm servers; PII masked before inference |
| **Hospital** needs RAG over patient records | Air-gapped deployment profile; no record ever leaves the datacenter |
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

## 🛡 Security Model

- **PII masking** runs before the prompt reaches the model — the model never sees raw sensitive data
- **Tool access** via MCP requires explicit adapter registration — no implicit function calling
- **Secrets** stay on-premise: never in prompts, logs, or exported artifacts
- **Production deployments** must define explicit allowlists for origins, tokens, and integrations
- See [SECURITY.md](SECURITY.md) for vulnerability reporting

---

## 🤝 Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR. The short version:

1. Fork → branch from `main` → PR with tests
2. No network calls in tests — treat them as bugs
3. Prefer small, auditable changes over large refactors

---

## License

MIT © [Zyrabit](https://zyrabit.com)
