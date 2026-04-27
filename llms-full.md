# Zyrabit Technical Reference for AI Agents

## Overview

Zyrabit is a local-first RAG platform with a Zero-Trust security layer and MCP bridge compatibility.

Core areas:

- `secure_agent.py`: secure CLI client.
- `zyrabit-slm/api-rag/app/main.py`: FastAPI API entrypoint.
- `zyrabit-slm/api-rag/app/services.py`: routing and model orchestration.
- `zyrabit-slm/api-rag/app/core/security/pii_pipeline.py`: PII sharding/anonymization pipeline.
- `zyrabit-slm/api-rag/app/api/v1/endpoints/mcp.py`: MCP-compatible endpoint.
- `zyrabit-slm/api-rag/app/core/telemetry_metrics.py`: Centralized business metrics .

## Design Principles

- **KISS (Keep It Simple, Stupid)**: Observability and instrumentation must be lightweight. Avoid complex abstractions unless strictly required for high-volume distributed tracing. Prefer native Prometheus metrics for business value.
- **Clean Git Tree**: All feature branches must originate from `beta`. Merge commits should be avoided in the `main` branch to maintain a linear and readable history. CI enforces a "Clean Tree" status for all production-ready releases.

## Security pipeline

1. Prompt enters API or CLI.
2. Text is sharded with overlap for contextual entity detection.
3. PII entities are replaced by deterministic per-request tokens.
4. Model receives tokenized prompt only.
5. Response is de-anonymized before returning to end-user.

Entity types currently handled:

- `email`
- `name` (context-based detection)
- `card` (with Luhn validation)
- `amount`
- `phone` (US-style numbers)
- `ssn` (Social Security numbers)

## Observability

Prometheus endpoint: `/metrics`

Custom metrics:

- `zyrabit_token_latency_ms_per_token{model=*, provider=*}`: Latency per token in ms.
- `zyrabit_token_usage_total{model=*, provider=*}`: Heuristic token usage counter.
- `zyrabit_security_hits_total{entity_type=*, action=rejected|masked}`: PII or spam interception tracker.

## Docker topology

- `frontend-network`: public entrypoint and UI/proxy.
- `backend-network`: API, vector DB, monitoring stack.
- `model-network` (`internal: true`): API + model engine only.

Traefik terminates TLS and applies rate limiting.

## MCP bridge contract

Config endpoint:

- `GET /mcp/config.json`

JSON-RPC endpoint:

- `POST /mcp`

Methods:

- `initialize`
- `tools/list`
- `tools/call`
- `resources/list`
- `resources/read`

Built-in tools:

- `secure_chat`
- `sanitize_text`
- `read_local_resource`

## Installer flow

`install.sh` is a bootstrap wrapper that clones the repository and delegates to `zyra-up.sh install`.

`zyra-up.sh` detects hardware profile:

- NVIDIA -> CUDA-capable runtime path
- Apple Silicon -> Metal-optimized path
- CPU-only -> quantized/smaller default model

Default model:

- `qwen2.5:7b` (or `qwen2.5:1.5b` when low RAM is detected)
