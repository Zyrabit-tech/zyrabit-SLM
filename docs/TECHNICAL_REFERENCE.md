# Zyrabit SLM — Technical Reference

## 1. Purpose and boundaries

Zyrabit SLM is a single-node document retrieval and local inference runtime. It accepts documents, produces chunks and embeddings, stores them in Chroma, retrieves context for a chat request, and forwards the composed prompt to an inference adapter. It is not a model-training system, multi-tenant platform, identity provider, or distributed database.

## 2. Runtime topology

| Component | Runtime | Responsibility | Persistent data |
| --- | --- | --- | --- |
| `zyrabit-web` | nginx | Serves Vite build; proxies API, MCP, Socket.IO | none |
| `zyrabit-api` | FastAPI | Chat, ingestion, state, tools, orchestration | SQLite WAL and uploaded documents |
| `zyrabit-db` | Chroma | Embeddings and document metadata | Chroma volume |
| inference provider | host or selected adapter | Generates embeddings and completions | provider-managed weights/cache |

The local compose profile exposes only `zyrabit-web` on `${ZYRABIT_LOCAL_PORT}:80`. Service discovery uses Docker DNS; no API or database port is published to the host.

## 3. Document pipeline

1. `POST /v1/ingest` writes an uploaded file to `DOCS_DIR`.
2. A FastAPI background task selects the processor by extension.
3. Audio/video files are transcribed to Markdown first.
4. `IngestUseCase` chunks text and writes vectors plus metadata through `ChromaAdapter`.
5. `HybridRetrieverService` updates its BM25 index.
6. A chat request retrieves vector and lexical candidates, optionally reranks them, injects the selected chunks into the prompt, and calls the configured provider.

Current limit: the BM25 index is reconstructed at API start from the active Chroma collection. It is process-local and not an independent persistent index.

## 4. State and memory

`SovereignStateManager` stores profiles, conversation records, and idempotency-related state in SQLite WAL. `SlidingWindowMemoryAdapter` supplies recent turns to the chat use case. Chroma stores retrieval material, not full conversation state. Deleting the `db_data` or `chroma-data` bind mount resets the respective state.

## 5. Interfaces

| Interface | Path | Auth | Use |
| --- | --- | --- | --- |
| REST | `/v1/*` | Bearer key | Chat, ingestion, profile, health |
| Socket.IO | `/socket.io` | Connection/session flow | Browser chat events |
| MCP discovery | `/mcp/config.json`, `/mcp/tools` | deployment policy | Tool metadata |
| MCP RPC | `/mcp/rpc` | deployment policy | `tools/list`, `tools/call` |

The browser uses `ZYRABIT_API_KEY_WEB`; external clients should use a distinct `ZYRABIT_API_KEY_*` value. `ApiKeyStore` loads every variable with that prefix when the API starts.

## 6. Inference adapters

The provider factory selects the adapter with `INFERENCE_PROVIDER`. Implementations exist for Ollama, Ollama streaming, MLX, embedded llama.cpp, vLLM, and an OpenAI-compatible endpoint. Adapters conform to inference ports so chat orchestration does not depend on provider HTTP details.

For local Docker + host Ollama, use `SLM_URL=http://host.docker.internal:11434`. On Linux, the local compose file adds the `host-gateway` mapping.

## 7. MCP extension contract

The in-process bridge exposes tools defined in `app/domain/services/mcp_service.py`. Add a tool there, provide a narrow input schema, register it with the service, and add a unit test in `api-rag/tests/test_mcp*.py`. The bridge must not execute arbitrary shell input or load unbounded filesystem paths.

The standalone `mcp/install_server.py` is separate from the API bridge and is intended for installation diagnostics. It has its own allowlist file: `mcp/mcp-tools-whitelist.yml`.

## 8. Operational commands

| Command | Effect |
| --- | --- |
| `./zyra.sh install` | Creates/updates local configuration, builds, starts, pulls selected models, probes health. |
| `./zyra.sh start` | Starts the selected compose profile. |
| `./zyra.sh verify` | Inspects expected containers and probes `/v1/health`. |
| `./zyra.sh stop` | Stops compose services without removing bind-mounted data. |
| `./zyra.sh dev` | Runs FastAPI with reload on port 8082; intended for API development only. |

## 9. Known engineering constraints

- The API catches infrastructure startup failures and can continue with partial services. Check `/v1/health` before declaring a node usable.
- Default local setup depends on a reachable Ollama process and downloaded chat/embedding models.
- The document upload endpoint uses the supplied filename directly after joining it with `DOCS_DIR`; filename normalization and upload size/type enforcement should be completed before exposing the API beyond a trusted local environment.
- Socket.IO is configured with permissive origins in `app/main.py`; restrict origins and authenticate the socket handshake in a public deployment.
- The local browser bearer token is a convenience mechanism, not a browser-secret mechanism. Put an authentication gateway in front of public deployments.

## 10. Verification baseline

Run unit tests after installing dependencies, build the UI, render compose configuration, then perform a manual smoke test: start the stack, upload a small text file, and ask a question whose answer is contained in that file. Verify health reports API, vector store, provider, and MCP statuses independently.
