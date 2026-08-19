<div align="center">

<img src="https://assets.zyrabit.com/logo_zyrabit.png" alt="Zyrabit SLM" width="120" />

# Zyrabit SLM

**Local-first sovereign AI runtime for private document retrieval, agentic workflows & local inference.**

[![CI](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/ci.yml/badge.svg)](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/ci.yml)
[![Security](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/security.yml/badge.svg)](https://github.com/Zyrabit-tech/zyrabit-SLM/actions/workflows/security.yml)
[![Version](https://img.shields.io/badge/v3.0.0--rc.1-Beta-3f5a6d?style=flat-square&labelColor=e2ecf4)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-6090b4?style=flat-square)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white&style=flat-square)](https://python.org)

[Quickstart](#-quickstart) · [Hardware Sizing](#-hardware-requirements--sizing) · [Benchmarks](#-inference--performance-baselines) · [Endpoints](#-service-endpoints--ports) · [Architecture](#-architecture) · [Security](SECURITY.md)

</div>

---

## 📌 Overview & Sovereign Scope

Zyrabit SLM is an enterprise-ready, **local-first AI runtime** designed for teams evaluating private document analysis, Retrieval-Augmented Generation (RAG), and autonomous ReAct agent execution without data egress. 

- **FastAPI Inference Gateway:** Real-time chat, streaming responses, and document retrieval.
- **Evidence-Bound RAG:** Ingests PDF, DOCX, CSV, audio (Whisper), and text into ChromaDB vector collections + BM25 keyword search.
- **Bi-directional PII Sanitization:** Masks sensitive data (names, IDs, credit cards, emails) before prompts reach inference engines and restores tokens on return.
- **Hardware-Agnostic Acceleration:** Seamlessly runs on Apple Silicon Metal, Tenstorrent Blackhole NPUs, NVIDIA CUDA GPUs, or multi-core x86/ARM CPUs.
- **Zero-Egress Air-Gap Profile:** Operates completely offline with 0 public DNS or outbound internet dependencies.

> **Notice**: Zyrabit SLM provides runtime isolation and PII guardrails for evaluation and deployment on customer-controlled infrastructure. It is not an automatic compliance certification (GDPR/HIPAA/ISO). Review your organizational threat model before processing classified or sensitive production data.

---

## 📊 Capability Matrix

| Capability | Status | Evidence / Verification | Execution Target |
| :--- | :---: | :--- | :--- |
| **Local Inference Engine** | `Beta` | Pluggable Ollama, MLX, llama.cpp, vLLM-TT | Apple Metal / CUDA / Tenstorrent / CPU |
| **Hybrid Document RAG** | `Beta` | Vector (Chroma) + BM25 in-memory keyword retrieval | Local storage & memory |
| **PII Guardrail Sandwich** | `Beta` | Regex + Luhn validation test suite (zero egress) | Inline pre/post inference pipeline |
| **ReAct Autonomous Agent** | `Beta` | Dynamic MCP tool calling with circuit-breaker | Local MCP Gateway (`:8001`) |
| **Air-gapped Execution** | `Validated` | `docker-compose.yml` internal isolated network | 100% offline with preloaded weights |
| **Observability & Telemetry** | `Beta` | Prometheus metrics + preconfigured Grafana dashboards | Local ports `:9090` / `:3000` |

---

## 🖥️ Hardware Requirements & Sizing

Zyrabit SLM autodetects host hardware on startup and selects the optimal model size and inference backend:

| Tier | Minimum Specs | Recommended Hardware | Target Models | Quantization / Formats |
| :--- | :--- | :--- | :--- | :--- |
| **Entry / Edge** | 8 GB RAM<br>4 CPU Cores | Intel/AMD x86_64, Mac M1/M2 (8GB) | Qwen 2.5 (1.5B – 3B)<br>Phi-3 Mini (3.8B)<br>DeepSeek-R1 (1.5B) | GGUF (Q4_K_M, Q5_K_M)<br>Ollama 4-bit |
| **Production / Standard** | 16 GB – 32 GB RAM<br>8+ CPU Cores / GPU | Apple Silicon M-Series (16GB+ Unified)<br>NVIDIA RTX 3060/4060+ (12GB+ VRAM)<br>Tenstorrent Blackhole p150 NPU | Qwen 2.5 (7B – 14B)<br>DeepSeek-R1 (7B)<br>Mistral (7B) | GGUF (Q4_K_M, Q8_0)<br>SafeTensors (FP16/BF16)<br>vLLM-TT Metalium |
| **Enterprise / MoE** | 32 GB – 64 GB+ RAM<br>Dedicated Accelerator | Apple Silicon Ultra / Max (36GB – 128GB)<br>NVIDIA RTX 4090 / A5000 / A100<br>Tenstorrent Multi-device cluster | Mixtral (8x7B MoE)<br>Qwen 2.5 (32B)<br>DeepSeek-R1 (14B – 32B) | GGUF (Q4_K_M)<br>SafeTensors / HF Hub<br>Multi-NPU sharded |

### Supported Model Formats
- **GGUF Format (`.gguf`):** Supported natively via embedded `llama.cpp` and Ollama (recommended: `Q4_K_M`, `Q5_K_M`, `Q8_0`).
- **Hugging Face Hub / SafeTensors:** Loaded via Hugging Face cache directory (`~/.cache/huggingface/hub`).
- **Ollama Registry:** Any tag from the official [Ollama Library](https://ollama.com/library) (e.g. `qwen2.5:7b`, `deepseek-r1:7b`, `mixtral:8x7b`).
- **Tenstorrent TT-NN:** Pre-compiled vLLM-TT Metalium graph weights for Blackhole / Wormhole NPUs.

---

## 📊 Inference & Performance Baselines

Real-world baseline metrics measured empirically on physical hardware running `./zyra.sh benchmark` with Grafana telemetry:

| Hardware Architecture | Inference Backend | Active Model | TTFT (Warm) | Generation Speed | Verification Date |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Tenstorrent Blackhole p150** | vLLM-TT Metalium (PCIe NPU) | `Qwen 2.5 (1.5B) / DeepSeek-R1` | `~800 ms` | **37.14 t/s** | `2026-08-19 (On-Device Verified)` |
| **Host x86 Multi-Core CPU** | llama.cpp / Ollama (AVX2) | `Qwen 2.5 (1.5B)` | `~145 ms` | **16.80 t/s** | `2026-08-19 (On-Device Verified)` |

*Telemetry Source: Metrics captured in-flight via Prometheus (`/metrics`) and visualized on Grafana dashboard (`http://localhost:3000`). Total turn latency includes PII masking, token sanitization, and state persistence.*

---

## 🏗 Architecture

```text
                    Client / Browser Request
                               │
                               ▼
               ┌───────────────────────────────┐
               │    API Gateway & Security     │  FastAPI + Traefik TLS Proxy
               │ Rate Limiting & Auth Guard    │
               └───────────────┬───────────────┘
                               │
                   ┌───────────▼───────────┐
                   │  PII Sanitization     │  In-flight Token Masking & Redaction
                   │  (Gatekeeper Filter)  │
                   └───────────┬───────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
        ┌────────▼────────┐         ┌────────▼────────┐
        │ Hybrid RAG Eng. │         │  Session Memory │  SQLite WAL (Sessions & Audit)
        │ Vector (Chroma) │         │  State Store    │  PostgreSQL (Production)
        │ + BM25 Keyword  │         └─────────────────┘
        └────────┬────────┘
                 │
        ┌────────▼──────────────────────────────────────────────┐
        │           Sovereign Inference Layer                   │
        │  • Apple Silicon Metal (Ollama / MLX)                 │
        │  • Tenstorrent Blackhole NPU (vLLM-TT Metalium)       │
        │  • NVIDIA CUDA GPU (Ollama / vLLM)                    │
        │  • CPU Multithreading (AVX2 / llama.cpp GGUF)         │
        └────────────────────────┬──────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │ Zero-Egress Response    │  Auditable, State-Preserved
                    └─────────────────────────┘
```

All traffic, embeddings, vector transformations, and inference tokens remain strictly local within your defined trust boundary.

---

## ⚡ Quickstart

**Prerequisites:** Python 3.12, [uv](https://github.com/astral-sh/uv), Docker & Docker Compose.

```bash
# 1. Clone repository
git clone https://github.com/Zyrabit-tech/zyrabit-SLM.git
cd zyrabit-SLM
chmod +x zyra.sh

# 2. Setup & Launch (Single entry-point command)
./zyra.sh install

# 3. Test local inference
curl -X POST http://localhost:8088/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(grep '^ZYRABIT_API_KEY_WEB=' zyrabit-slm/.env | cut -d= -f2-)" \
  -d '{"text": "Summarize our sovereign architecture capabilities"}'
```

> [!TIP]
> **Avoid using `sudo ./zyra.sh`**: Running scripts with `sudo` creates root-owned files that disrupt user permissions. If you encounter Docker permission issues, add your user to the docker group: `sudo usermod -aG docker $USER && newgrp docker`.

### Operational Commands

| Command | Purpose |
| :--- | :--- |
| `./zyra.sh install` | **Single setup & launch command** (guided config on first run, smart re-runs) |
| `./zyra.sh install -y` | Silent automated setup using existing `.env` without interactive prompts |
| `./zyra.sh start` | Re-launch existing container stack without reconfiguration |
| `./zyra.sh stop` | Tear down all runtime containers and profiles |
| `./zyra.sh verify` | Health check: container lifecycle status and HTTP API probes |
| `./zyra.sh benchmark` | Run live inference throughput (t/s) and TTFT benchmark against active model |
| `./zyra.sh audit` | Generate 0-egress compliance and PII verification report |
| `./zyra.sh validate` | Execute full offline QA test suite (tests, architecture boundaries, air-gap) |

---

## 🌐 Service Endpoints & Ports

In **Local / Dev Mode** (default), direct service ports are exposed for easy debugging and low latency:

| Service | Local Dev URL | Direct Port | Description |
| :--- | :--- | :---: | :--- |
| **Interactive Web UI** | [`http://localhost:8080`](http://localhost:8080) | `8080` | Document workspace & sovereign chat interface (Vite / Nginx) |
| **Chat & Inference API** | [`http://localhost:8088/v1`](http://localhost:8088/v1) | `8088` | FastAPI backend (RAG pipeline, PII sanitization, chat routing) |
| **API Health Probe** | [`http://localhost:8088/v1/health`](http://localhost:8088/v1/health) | `8088` | Liveness & readiness probe with active provider capabilities |
| **Grafana Telemetry** | [`http://localhost:3000`](http://localhost:3000) | `3000` | Real-time TPS, TTFT, token latency & hardware metrics |
| **Prometheus Engine** | [`http://localhost:9090`](http://localhost:9090) | `9090` | Time-series metrics scraper & alerting rules |
| **Vector DB (Chroma)** | [`http://localhost:8000`](http://localhost:8000) | `8000` | Local vector embedding store |
| **MCP Tool Server** | [`http://localhost:8001`](http://localhost:8001) | `8001` | Model Context Protocol agent tool execution server |
| **Hardware Engine (TT)** | [`http://localhost:8090`](http://localhost:8090) | `8090` | Tenstorrent vLLM-TT hardware acceleration inference server |

> **Production Deployments (Traefik TLS):** When launched with `--production`, all external traffic is routed securely via Traefik over HTTPS (`port 443`) with path-based routing: `https://${DOMAIN}/` routes to the Web UI, and `https://${DOMAIN}/v1` routes to the API.

---

## 🖥️ Interface & Walkthrough

<div align="center">

### 1. Interactive CLI & Hardware Discovery
*Unified CLI launcher (`./zyra.sh`) displaying system status, hardware detection, and runtime configuration.*

<br/>

<img src="https://assets.zyrabit.com/public/images/zyrabit-CLI.png" alt="Zyrabit SLM CLI Welcome Screen" width="850" />

<br/><br/>

### 2. Guided Configuration Setup
*Step-by-step installation and stack configuration for sovereign local deployments.*

<br/>

<img src="https://assets.zyrabit.com/public/images/zyrabit-setup.png" alt="Zyrabit SLM Setup" width="850" />

<br/><br/>

### 3. Interactive Web UI & Document Workspace
*Sovereign document ingestion, hybrid RAG chat, and live telemetry interface.*

<br/>

<img src="https://assets.zyrabit.com/public/images/zyrabit-web.png" alt="Zyrabit SLM Web UI Document Workspace" width="850" />

</div>

---

## 🤖 AI Agent Setup (Cursor, Antigravity, Windsurf, Cline)

If you are using an AI coding assistant to configure, troubleshoot, or build tools on Zyrabit SLM, copy and paste the prompt below into your assistant's chat or system instructions.

### 📋 Setup & Autonomous Troubleshooting Prompt

```text
You are pair-programming on Zyrabit SLM, a sovereign, local-first AI runtime.

Task: Setup, verify, and operate the local Zyrabit SLM environment.

1. Environment & Permissions Check:
   - Check if Docker daemon is running and user has docker permissions (no root/sudo needed).
   - Ensure scripts have executable permissions: `chmod +x zyra.sh`
   - Run `python3 --version` (requires Python 3.12) and check if `uv` is installed.
   - Check if Ollama is running locally: `curl -s http://localhost:11434/api/tags` or if local GGUF models exist.

2. Installation & Configuration:
   - Run `uv sync --all-groups` to synchronize the virtual environment.
   - Run `./zyra.sh install` (or `./zyra.sh start` if already configured).
   - Local models in Ollama, HF cache, or ~/models will be auto-detected.

3. Health & Sanity Checks:
   - Check container status: `./zyra.sh verify`
   - Test health endpoint: `curl -s http://localhost:8088/v1/health`
   - Test local inference:
     curl -X POST http://localhost:8088/v1/chat \
       -H "Content-Type: application/json" \
       -H "Authorization: Bearer <ZYRABIT_API_KEY_WEB>" \
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
      "ZYRABIT_API_URL": "http://localhost:8088",
      "ZYRABIT_API_KEY": "zyrabit-local-token"
    }
  }
}
```

---

## 🔍 Real-world Use Cases

| Scenario | What Zyrabit SLM does |
|---|---|
| **Legal firm** asks AI to review contracts | Documents stay on firm servers; PII masked before inference |
| **Hospital** needs RAG over patient records | Air-gapped deployment profile; no patient record ever leaves the datacenter |
| **Bank** runs internal compliance Q&A | Audit log of every query, model response, and retrieved chunk |
| **Government agency** deploys on classified infra | Fully offline after initial setup; Ollama / GGUF local model weights |
| **Enterprise IT** builds internal knowledge bot | Grafana dashboard shows latency, model load, and query volume |

---

## 📦 Stack Components

```text
zyrabit-slm/
├── api-rag/              # FastAPI app — inference, RAG, PII pipeline, audit
├── config/               # Environment-specific configuration
├── prompts/              # Versioned system prompts (auditable artifacts)
├── web-ui/               # Browser interface for local interaction (Vite/Tailwind)
├── grafana/              # Dashboards — latency, throughput, model health
├── prometheus/           # Metrics collection and alerting rules
├── traefik/              # Reverse proxy, TLS, routing (production only)
├── scripts/              # Operational helpers
├── docker-compose.yml    # Unified stack (Local & Production profiles)
mcp/                      # Model Context Protocol server (controlled tool access)
validation/               # Validation scripts and compliance artifacts
zyra.sh                   # Unified CLI: install · start · stop · verify · benchmark
zyra-up.sh                # Legacy shim → delegates to zyra.sh
```

---

## 🧪 Testing & Validation

```bash
# All unit tests (runs 100% offline)
uv run pytest zyrabit-slm/api-rag/tests/unit -q

# Sovereign QA validation (PII + architecture boundaries + air-gap)
./zyra.sh validate
```

> **Invariant**: If a test reaches the network, it is treated as a critical bug. The entire test suite runs strictly offline.

---

## 🛡 Security Model

- **PII masking** runs before the prompt reaches the model — the model never sees raw sensitive data.
- **Tool access** via MCP requires explicit adapter registration — no implicit function calling.
- **Secrets** stay on-premise: never in prompts, logs, or exported artifacts.
- **Production deployments** enforce strict credential generation, Traefik TLS, and origin allowlists.
- See [SECURITY.md](SECURITY.md) for vulnerability reporting and architecture details.

---

## 🤝 Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR. The core requirements:

1. Fork → branch from `main` → PR with tests.
2. No network calls in tests — strictly offline execution.
3. Prefer small, auditable changes over large refactors.

---

## License

MIT © [Zyrabit](https://zyrabit.com)
