---
sidebar_position: 0
title: Zyrabit SLM — Platform Overview
description: Zyrabit SLM is a sovereign AI infrastructure stack for regulated environments. Run language models entirely on your own infrastructure with no external API dependencies.
---

# Zyrabit SLM

**Sovereign AI infrastructure for regulated environments.**

Zyrabit SLM is a production-grade AI runtime that enables organizations to operate language models entirely on their own infrastructure — with no external API calls, no data leakage, and a complete audit trail. It is designed for environments where data sovereignty is non-negotiable: healthcare, finance, legal, government, and enterprise IT.

---

## What Zyrabit SLM Actually Is

Zyrabit SLM is not a model. It is a **local-first AI runtime** composed of containerized services that work together to deliver a private, auditable, and air-gap capable inference environment.

| Layer | Component | What it does |
|---|---|---|
| **Inference** | Ollama + local model weights | Runs the language model entirely on your hardware |
| **API** | FastAPI (`zyrabit-api`) | Exposes `/v1/chat`, `/v1/ingest`, `/v1/models` — the interface to your AI |
| **Privacy** | PII Gatekeeper | Intercepts and masks sensitive data before it reaches the model |
| **Memory** | ChromaDB (`zyrabit-db`) | Vector database for RAG — your documents, searchable by meaning |
| **Tool Access** | MCP Server (`zyrabit-mcp`) | Controlled, auditable access to system tools via Model Context Protocol |
| **State** | SQLite (WAL mode) | Session memory, audit logs, conversation history — all local |
| **Observability** | Prometheus + Grafana | Latency, throughput, TTFT, model health — real-time |
| **Routing** | Traefik | TLS termination, rate limiting, reverse proxy — production-grade ingress |
| **Automation** | n8n (optional) | Workflow automation connecting your business systems to Zyrabit |
| **Web UI** | React (`zyrabit-web`) | Browser-based chat interface for direct interaction |

---

## Architecture

```text
              Client Request (HTTP/HTTPS)
                        │
                        ▼
           ┌────────────────────────┐
           │  Traefik (Port 80/443) │  TLS termination, rate limiting, routing
           └───────────┬────────────┘
                       │
                       ▼
           ┌────────────────────────┐
           │     PII Gatekeeper     │  Masks emails, IDs, API keys before inference
           └───────────┬────────────┘
                       │
             ┌─────────┴──────────┐
             ▼                    ▼
    ┌─────────────────┐  ┌────────────────┐
    │   RAG Engine    │  │   State Store  │  SQLite WAL
    │  (ChromaDB)     │  │  (Audit + Memory)│
    └────────┬────────┘  └────────────────┘
             │
   ┌─────────▼──────────────────┐
   │     Inference Layer        │  Ollama-compatible
   │  (Ollama / Metal / CUDA /  │  Qwen2.5, Mistral, Llama3, etc.
   │   Tenstorrent)             │
   └────────────────────────────┘
```

All data remains within your trust boundary. No outbound calls during inference.

---

## Real-World Use Cases

| Deployment | What Zyrabit does |
|---|---|
| **Legal firm — contract review** | Documents stay on firm servers; PII masked before inference; full audit trail per query |
| **Hospital — patient record Q&A** | Air-gapped, HIPAA-aligned; no PHI leaves the datacenter; ChromaDB stores vectorized records locally |
| **Bank — compliance Q&A** | Every query, response, and retrieved chunk is logged in SQLite for regulatory review |
| **SME — internal knowledge bot (Zyrabit Rada)** | Upload your SOPs, manuals, pricing docs; your team queries them in natural language via the web UI |
| **Government — classified infra** | Fully offline after initial setup; Ollama + local model weights; no cloud dependencies |
| **DevOps team — infrastructure assistant** | MCP server connected to Claude Desktop or Cursor for AI-assisted operations with explicit tool allowlists |

---

## Deployment Modes

| Mode | Command | Use case |
|---|---|---|
| **Local** (default) | `./zyra-up.sh` | macOS development, teams without SSL certs |
| **Production** | `./zyra-up.sh --production` | On-premise servers with Traefik + TLS |
| **Automation** | `./zyra-up.sh start --profile automation` | Enables n8n at `https://localhost/n8n` |
| **Dev (native)** | `./zyra-up.sh dev` | FastAPI hot-reload for API development |
| **Tenstorrent** | `./zyra-up.sh start --profile tenstorrent` | Hardware accelerator for P150 Blackhole |

---

## Key Design Principles

**Zero Trust by Default.** Network isolation is enforced at the Docker level. The model inference network (`model-network`) is flagged `internal: true` — the model container cannot make outbound connections.

**PII masking before inference.** The Gatekeeper intercepts every prompt. Raw sensitive data never reaches the model. If you send `"My SSN is 123-45-6789"`, the model receives `"My SSN is <SSN_1>"`.

**Explicit tool access.** The MCP server only exposes tools defined in `mcp-tools-whitelist.yml`. No implicit function calling. No shell injection.

**Offline-capable.** After initial dependency download, the stack requires no internet connectivity.

**Auditable state.** Every inference request, retrieved chunk, and model response is logged in SQLite with a session ID.

---

## Quick Navigation

- **First time on macOS?** → [macOS Quickstart](./getting-started/macos-quickstart)
- **Setting up a bare-metal server?** → [Bare-Metal Setup](./getting-started/bare-metal-setup)
- **Configure your AI agent persona?** → [Agent Personality](./agents-and-personality)
- **Connect Claude Desktop or Cursor?** → [MCP Server](./mcp-server)
- **Build automation workflows?** → [n8n Integration](./n8n-automation)
- **API reference?** → [API Reference](./api-reference)
