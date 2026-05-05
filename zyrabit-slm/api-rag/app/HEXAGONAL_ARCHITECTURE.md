# Zyrabit Hexagonal Architecture — Sovereign Pattern (V5.0)

This project applies **Hexagonal Architecture (Ports & Adapters)** to ensure the core domain logic is completely decoupled from infrastructure concerns (databases, LLM engines, transport protocols).

---

## Layer Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    PRIMARY ADAPTERS (Driving)                │
│          FastAPI REST endpoints  ·  Socket.IO handlers       │
└───────────────────────────┬─────────────────────────────────┘
                            │ calls
┌───────────────────────────▼─────────────────────────────────┐
│                     SECURITY PIPELINE                        │
│         PII anonymization interceptors (core/security)       │
│         Runs BEFORE domain logic on every request            │
└───────────────────────────┬─────────────────────────────────┘
                            │ sanitized input
┌───────────────────────────▼─────────────────────────────────┐
│                       DOMAIN LAYER                           │
│   ChatUseCase.execute()  ·  Gatekeeper  ·  IngestUseCase     │
│   HybridRetrieverService  ·  Cache                           │
└──────────────┬──────────────────────────┬───────────────────┘
               │ via Ports                │ via Ports
┌──────────────▼──────────┐   ┌──────────▼──────────────────┐
│   InferencePort          │   │   VectorStorePort            │
│   OllamaInferenceAdapter │   │   ChromaAdapter              │
│   OpenAICompatAdapter    │   │   HybridRetrieverService     │
└─────────────────────────┘   └──────────────────────────────┘
```

---

## Layer Descriptions

### 1. Primary Adapters (`app/api/v1/`)
The **driving side** — triggers that start the application's work.

- `endpoints/chat.py` — `POST /v1/chat`, receives user queries.
- `endpoints/health.py` — `GET /v1/health`, liveness and readiness probes.
- `endpoints/documents.py` — `POST /v1/ingest`, document ingestion.
- `endpoints/mcp.py` — JSON-RPC MCP bridge.
- Socket.IO handlers in `main.py` — real-time chat.

### 2. Security Pipeline (`app/core/security/`)
Runs **before** domain logic on every inbound request. This is not a middleware — it is a deliberate interception layer.

- `pii_pipeline.py` — detects and replaces PII with typed tokens (`<USER_EMAIL_1>`, `<PHONE_1>`, etc.).
- Uses **Luhn validation** for credit cards, regex for emails/phones/SSN/amounts, and contextual name detection.
- **De-anonymization** is applied to the model response before returning to the user.

### 3. Domain Layer (`app/domain/`)

#### Use Cases (`use_cases/`)
Orchestrate application workflows without knowledge of infrastructure:

| Use Case | Responsibility |
|---|---|
| `ChatUseCase.execute()` | Full pipeline: PII mask → route → retrieve → infer → cache |
| `IngestUseCase` | Document validation → chunking → vector store population |

#### Domain Services (`services/`)

| Service | Responsibility |
|---|---|
| `Gatekeeper` | Routing decision: `"rag"` / `"direct"` and PII masking |
| `HybridRetrieverService` | BM25 keyword + ChromaDB vector search fusion |
| `mcp_service.py` | MCP protocol implementation and tool dispatch |

> **V5.0 routing values:** `"rag"`, `"direct"`. The `"reject"` route was removed — off-topic queries are handled contextually by the SLM with the system prompt.

### 4. Ports (`app/ports/`)
Abstract contracts that the domain depends on. Infrastructure must implement these.

| Port | Contract |
|---|---|
| `InferencePort` | `generate(request) → InferenceResult` |
| `VectorStorePort` | `similarity_search()`, `add_texts()`, `heartbeat()` |
| `AutomationPort` | Webhook adapter contract for n8n and future integrations |

### 5. Secondary Adapters — Infrastructure (`app/infrastructure/`)
The **driven side** — implementations of the ports.

| Adapter | Port | Technology |
|---|---|---|
| `OllamaInferenceAdapter` | `InferencePort` | Ollama HTTP API |
| `ChromaAdapter` | `VectorStorePort` | ChromaDB + LangChain |
| `DirectOllamaEmbeddings` | Embeddings | Ollama embeddings endpoint |
| `n8nWebhookAdapter` | `AutomationPort` | HMAC-signed webhooks |

### 6. Core (`app/core/`)
Cross-cutting concerns shared across layers.

| Module | Purpose |
|---|---|
| `security/pii_pipeline.py` | PII detection, anonymization, de-anonymization |
| `shared/config.py` | Environment variable loading |
| `shared/metrics.py` | Prometheus counters and histograms |
| `shared/logger.py` | Structured JSON logging |

---

## Data Flow (V5.0)

```
Client Request
    │
    ▼
FastAPI endpoint (Primary Adapter)
    │
    ▼
ChatUseCase.execute(text)
    ├─ 1. Gatekeeper.mask_pii(text)          → sanitized_text, entities
    ├─ 2. Gatekeeper.get_routing_decision()  → "rag" | "direct"
    ├─ 3. [if "rag"] HybridRetrieverService.search() → context chunks
    ├─ 4. InferencePort.generate(prompt)     → model response
    └─ 5. Cache.set() (if client_msg_id)
    │
    ▼
Response to client
```

---

## Extension Guide

### Adding a new inference provider

1. Create `app/infrastructure/inference/my_provider_adapter.py` implementing `InferencePort`.
2. Register it in `app/inference_factory.py`.
3. Set `INFERENCE_PROVIDER=my_provider` in `.env`.

### Adding a new external integration (n8n, Make, etc.)

1. Create an adapter implementing `AutomationPort` in `app/adapters/`.
2. Add the corresponding FastAPI router under `app/api/v1/endpoints/`.
3. Reference the blueprint: `app/adapters/make_adapter_blueprint.py`.

### Adding a new PII pattern

1. Add the regex detector to `app/core/security/pii_pipeline.py`.
2. Add corresponding test cases in `tests/test_pii_pipeline.py` and `tests/test_security.py`.
