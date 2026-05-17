# 🤖 Zyrabit SLM

[![Version](https://img.shields.io/badge/version-2.0.0-orange.svg)](VERSION)
[![CI](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/ci.yml/badge.svg)](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/ci.yml)
[![Security Audit](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/security.yml/badge.svg)](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/security.yml)
[![Docker Hub](https://img.shields.io/badge/docker-zyrabitcore-blue.svg)](https://hub.docker.com/r/zyrabitcore/zyrabit-slm)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

**Sovereign Operating System for Local AI: Persistent memory, hardware-aware orchestration, and native MCP v1.0.**

---

## 🏛️ Architecture Topology

Zyrabit is designed as a zero-trust, air-gapped capable AI stack.

```text
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

---

## 💎 Sovereign Features (Zyrabit SLM v2.0)

*   **Zero-Lag Command Router (<15ms)**: Direct interceptor for commands like `/stats`, `/vault`, `/clear`, `/tools` that bypasses LLM inference completely using SQLite state lookup.
*   **FTS5 Hybrid RAG (<200ms)**: Hybrid keyword (FTS5 SQLite table virtual) and vector (ChromaDB) retrieval pipeline prioritizing fast local index lookup before vector fallback.
*   **Obsidian Brain Sync**: Recursive scanning and ingestion of Markdown vaults into the secure RAG engine.
*   **AutoLearner Background Loop**: An asynchronous background service that periodically synthesizes chat history and generates reflective self-learning notes written directly back to your Obsidian vault.
*   **Dynamic Sovereign Identity**: Personalized assistant name locked dynamically through onboarding across Web and Telegram (eliminating hardcoded "Kai" references).

---

## 🚀 Quick Start (The Sovereign Way)

Zyrabit uses a unified orchestration script to manage your local infrastructure.

```bash
# 1. Clone the repository
git clone https://github.com/Zyrabit-tech/zyrabit-SLM.git
cd zyrabit-SLM

# 2. Configure your environment
cp zyrabit-slm/example.env zyrabit-slm/.env
# Edit .env to set your SLM_URL and DB_URL

# 3. System Check & Install
./zyra-up.sh doctor     # Check RAM and hardware acceleration
./zyra-up.sh install    # Build images, start stack, and pull models
```

---

## 🛠️ CLI Tool: `zyra-up.sh`

The `zyra-up.sh` script is your primary interface for managing the Zyrabit lifecycle.

| Command | Description |
|---|---|
| `install` | Full setup: build images, start stack, and pull AI models |
| `start` | Bring up the infrastructure only |
| `stop` | Tear down the infrastructure |
| `build` | Build Docker images without starting containers |
| `verify` | Visual health check of all services and API probes |
| `dev` | Native local development using `uv` with hot-reload |
| `doctor` | Diagnostic: validate environment, RAM, and hardware |

---

## 🐳 Docker Hub & Sovereign Images

We provide pre-built, production-ready images for the Zyrabit stack.

> [!TIP]
> You can find our official images at **[Docker Hub: zyrabitcore/zyrabit-slm](https://hub.docker.com/r/zyrabitcore/zyrabit-slm)**.
> Use these images if you prefer not to build locally or if you are deploying to an air-gapped environment.

```bash
# Pull the latest stable version
docker pull zyrabitcore/zyrabit-slm:2.0.0
```


---

## 🔒 Security & Privacy

Zyrabit is built on a **Security-First** philosophy:

*   **PII Scrubbing**: A heuristic pipeline anonymizes sensitive data (emails, SSNs, etc.) *before* it leaves the `api-rag` container.
*   **Isolated Models**: The `model-network` has no external access (`internal: true`).
*   **Zero-Trust Ingress**: Traefik handles all incoming traffic with rate-limiting and TLS.

---

## 📂 Repository Structure

*   `zyrabit-slm/`: The core Docker stack (API, UI, MCP, Config).
*   `internal/`: Engines and hardware-specific bridges (Tenstorrent).
*   `mcp/`: Model Context Protocol server implementation.
*   `validation/`: Pentest checklists and performance benchmarks.
*   `zyra-up.sh`: Unified orchestration CLI.

---

## 📖 Extended Documentation

*   🤝 **[Contributing](CONTRIBUTING.md)**: How to help us build the future of sovereign AI.
*   🔒 **[Security Policy](SECURITY.md)**: Vulnerability disclosure and privacy standards.
*   🏗️ **[Hexagonal Architecture](zyrabit-slm/api-rag/app/HEXAGONAL_ARCHITECTURE.md)**: Deep dive into the backend design.
*   🐳 **[Docker Debugging](DOCKER_DEBUG_GUIDE.md)**: Troubleshooting common container issues.
*   📡 **[cURL Examples](zyrabit-slm/docs/CURL_EXAMPLES.md)**: How to interact with the API.

---

## 📜 License

MIT © Zyrabit
