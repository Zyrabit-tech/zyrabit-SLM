---
sidebar_position: 1
title: 'macOS Quickstart (Apple Silicon)'
description: 'Deploy Zyrabit SLM on macOS with Apple Silicon using native Metal acceleration and Ollama as the local inference engine.'
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# macOS Quickstart (Apple Silicon)

> **Audience**: Engineers running macOS on M1, M2, or M3 hardware who want a fully sovereign, local AI stack with hardware-accelerated inference.

This guide is specific to **macOS with Apple Silicon (arm64)**. On this platform, Zyrabit SLM runs Ollama natively on the host — outside Docker — so the macOS Metal Performance Shaders (MPS) framework provides GPU acceleration directly, with no containerization overhead on the inference path. All other services (API, Web UI, ChromaDB, Grafana, Prometheus) run in Docker via `docker-compose.local.yml`.

---

## Why macOS Gets a Dedicated Guide

On Linux or Windows, the `zyrabit-engine` (Ollama) container runs inside Docker. On macOS with Apple Silicon, that container is **deliberately disabled** in `docker-compose.local.yml`:

```yaml
# 2. THE MUSCLE: SLM Server (DISABLED - Using Native Metal)
# zyrabit-engine:
#   image: ollama/ollama:latest
#   ...
```

Instead, `zyra-up.sh` detects the host OS and chip architecture at startup:

```bash
elif [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
    accelerator="metal"
    export SLM_URL="http://host.docker.internal:11434"
fi
```

The API container reaches the host-native Ollama process via the Docker special hostname `host.docker.internal`, mapped through the `extra_hosts` entry in `docker-compose.local.yml`:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

This means:
- **Inference runs on Metal** — no CPU emulation, no virtualization penalty.
- **All other services run in Docker** — identical to every other deployment target.
- The API port is remapped to `8082:8080` to avoid conflicts with macOS system services that commonly bind `8080`.

---

## Prerequisites

Ensure the following tools are installed and running **before** cloning the repository.

| Tool | Version / Notes | Install |
|---|---|---|
| macOS | Ventura 13+ recommended | — |
| Docker Desktop for Mac | ARM-native build (do **not** enable Rosetta for `x86_64` emulation) | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |
| Ollama for macOS | Latest stable | [ollama.com/download/mac](https://ollama.com/download/mac) |
| `uv` (Python manager) | Any recent version | See below |
| Git | Any | `xcode-select --install` |

### Install `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reload PATH so the shell can find uv
source $HOME/.local/bin/env

# Verify
uv --version
```

### Install and start Ollama

Download the macOS `.zip` from [ollama.com/download/mac](https://ollama.com/download/mac), move `Ollama.app` to `/Applications`, and launch it. Ollama runs as a menu bar process and exposes its API on `http://127.0.0.1:11434`.

Pull the default models that `zyra-up.sh` selects for systems with 12 GB RAM or more:

```bash
ollama pull qwen2.5:7b
ollama pull mxbai-embed-large
```

:::note Model selection by RAM
`zyra-up.sh` automatically selects the model based on detected RAM:
- **>= 12 GB RAM** -> `qwen2.5:7b` (default)
- **< 12 GB RAM** -> `qwen2.5:1.5b`

To override: `./zyra-up.sh install --model llama3.2:3b`
:::

### Verify Ollama is running

`zyra-up.sh` uses this exact probe internally before deciding whether to use native Ollama:

```bash
curl -s -m 2 http://127.0.0.1:11434/api/tags
```

A JSON response listing available models confirms Ollama is reachable. If the command times out, open the Ollama app from `/Applications` or restart it from the menu bar.

### Docker Desktop prerequisite checklist

- Open Docker Desktop -> **Settings -> General**: confirm "Use Virtualization Framework" is enabled.
- Confirm Rosetta emulation is **disabled** (Settings -> Features in development): Zyrabit images are built for `linux/arm64` and do not require Rosetta.
- Confirm Docker Desktop is running: `docker info` should return without error.

---

## First-Time Setup

### 1. Clone the repository

```bash
git clone https://github.com/Zyrabit-tech/zyrabit-SLM.git
cd zyrabit-SLM
```

### 2. Configure the environment

```bash
cp zyrabit-slm/example.env zyrabit-slm/.env
```

Open `zyrabit-slm/.env` and review the defaults. The values in `example.env` work out of the box for local macOS development. Key variables:

```bash
# API token used by the Web UI (do not change unless you update the UI config)
ZYRABIT_API_KEY_WEB=zyrabit-local-token

# Token used by the MCP server
ZYRABIT_API_KEY_MCP=zyrabit-mcp-token

# Inference provider — set to ollama for local Ollama
INFERENCE_PROVIDER=ollama

# In local mode, zyra-up.sh overrides this to http://host.docker.internal:11434 automatically
SLM_URL=http://zyrabit-engine:11434

# Vector database URL (ChromaDB container)
DB_URL=http://zyrabit-db:8000

# Default model — must already be pulled in Ollama
MODEL_NAME=qwen2.5:7b

# Embedding model — must already be pulled in Ollama
EMBEDDING_MODEL=mxbai-embed-large
```

:::important Grafana and Prometheus auth in local mode
`docker-compose.local.yml` sets `GF_AUTH_ANONYMOUS_ENABLED=true` and `GF_AUTH_BASIC_ENABLED=false` for Grafana, so no login is required in macOS local mode. The `PROMETHEUS_BASIC_AUTH` and `GRAFANA_BASIC_AUTH` variables in `.env` are only enforced in production (Traefik) mode.
:::

### 3. Start the stack

`USE_LOCAL=true` is the default in `zyra-up.sh` (version 2.3.0+), so no flags are required for macOS local mode:

```bash
./zyra-up.sh start
```

To perform a full install (build images + start + model pull) on first run:

```bash
./zyra-up.sh install
```

On macOS with native Ollama detected, the script skips the `zyrabit-engine` container automatically:

```
ℹ Using native Ollama (host). Skipping zyrabit-engine container...
```

Internally, this is equivalent to:

```bash
docker compose -f zyrabit-slm/docker-compose.yml \
               -f zyrabit-slm/docker-compose.local.yml \
               up -d --scale zyrabit-engine=0
```

---

## How macOS Local Mode Works

The following diagram shows the service topology in local mode:

```
+-----------------------------------------------------------+
|  macOS Host (arm64)                                       |
|                                                           |
|  +----------------+    host.docker.internal:11434         |
|  | Ollama.app     |<---------------------------------+    |
|  | (Metal/MPS)    |                                 |    |
|  +----------------+                                 |    |
|                                                     |    |
|  +----------------------------------------------+  |    |
|  |  Docker Desktop (linux/arm64 containers)     |  |    |
|  |                                              |  |    |
|  |  zyrabit-api  (:8082) --- SLM_URL -----------+  |    |
|  |       |                                         |    |
|  |  zyrabit-web  (:3000)                           |    |
|  |  zyrabit-db   (:8000)  [ChromaDB]               |    |
|  |  zyrabit-grafana (:3001)                        |    |
|  |  zyrabit-prometheus   [internal only]           |    |
|  |  zyrabit-mcp  (:8001)                           |    |
|  +----------------------------------------------+  |    |
+-----------------------------------------------------------+
```

The API container is configured in `docker-compose.local.yml` with:

```yaml
environment:
  - SLM_URL=http://host.docker.internal:11434
extra_hosts:
  - "host.docker.internal:host-gateway"
```

This routes all inference requests from the `zyrabit-api` container to the native Ollama process running on the macOS host, bypassing Docker networking for the most latency-sensitive path.

---

## Service URLs

All services in macOS local mode are reachable at `localhost`. Ports differ from production mode.

| Service | Container | URL | Notes |
|---|---|---|---|
| Web UI | `zyrabit-web` | http://localhost:3000 | Nginx, serves the SPA |
| API (RAG + Chat) | `zyrabit-api` | http://localhost:8082/v1 | Port remapped from 8080 |
| Grafana | `zyrabit-grafana` | http://localhost:3001 | No login required in local mode |
| ChromaDB | `zyrabit-db` | http://localhost:8000 | Vector store |
| MCP Server | `zyrabit-mcp` | http://localhost:8001 | Model Context Protocol |
| Ollama (host) | — | http://127.0.0.1:11434 | Native process, not a container |

---

## Verify the Stack is Healthy

### Using `zyra-up.sh`

```bash
# Health check: validate all containers and API status
./zyra-up.sh verify

# Full environment diagnostics: RAM, cores, accelerator detection, Ollama probe
./zyra-up.sh doctor
```

`doctor` output on a healthy M2 system should include:

```
  Hardware Profile: METAL (RAM: 16GB, Cores: 8)
  Accelerator:  metal
✔ Local Ollama detected on host (Metal).
✔ System environment is healthy.
```

`verify` handles the case where `zyrabit-engine` is not running as a container — it detects native Ollama and reports it as `native (metal) / healthy`:

```
CONTAINER                 STATUS          HEALTH
------------------------- --------------- ----------
zyrabit-api               running         healthy
zyrabit-web               running         healthy
zyrabit-engine            native (metal)  healthy
zyrabit-db                running         healthy
```

### Manual container check

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### API health endpoint

```bash
curl http://localhost:8082/v1/health
```

A healthy response returns HTTP `200` with a JSON body indicating service status.

---

## Run Your First Inference Query

All API requests are authenticated with a Bearer token. The default token for the Web UI — as defined in `example.env` — is `zyrabit-local-token`.

### Chat query

```bash
curl -X POST http://localhost:8082/v1/chat \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer zyrabit-local-token' \
  -d '{"messages": [{"role": "user", "content": "What can you tell me about our infrastructure?"}]}'
```

### List available models

```bash
curl http://localhost:8082/v1/models \
  -H 'Authorization: Bearer zyrabit-local-token'
```

The response lists models currently available in the host Ollama instance.

:::tip Token reference
`zyrabit-local-token` is the value of `ZYRABIT_API_KEY_WEB` in `.env` (sourced from `example.env`).  
`zyrabit-mcp-token` is the value of `ZYRABIT_API_KEY_MCP`, used by the MCP server.
:::

---

## Ingest Your First Document

The ingest endpoint accepts PDF, DOCX, and plain text files. Documents are chunked (default: 1000 characters, 200 overlap as configured in `.env`), embedded using `mxbai-embed-large`, and stored in ChromaDB under the `zyrabit_knowledge` collection.

```bash
curl -X POST http://localhost:8082/v1/ingest \
  -H 'Authorization: Bearer zyrabit-local-token' \
  -F 'file=@/path/to/document.pdf'
```

Replace `/path/to/document.pdf` with an actual file path. After ingestion completes, subsequent chat queries will retrieve relevant chunks from that document to ground the model's response.

RAG configuration in `.env`:

```bash
RAG_COLLECTION=zyrabit_knowledge
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

---

## View Metrics in Grafana

In macOS local mode, Grafana runs on port `3001` with anonymous access enabled — no login is required.

1. Open http://localhost:3001 in your browser.
2. Navigate to **Dashboards** in the left sidebar.
3. Select the pre-provisioned **Zyrabit** dashboard.

The dashboard surfaces metrics scraped by Prometheus from the `zyrabit-api` container, including:

- **TTFT (Time to First Token)** — `zyrabit_ttft_seconds`
- Request throughput and error rates
- ChromaDB query latency

Grafana local-mode configuration from `docker-compose.local.yml`:

```yaml
environment:
  - GF_AUTH_ANONYMOUS_ENABLED=true
  - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
  - GF_AUTH_BASIC_ENABLED=false
  - GF_SERVER_ROOT_URL=http://localhost:3001
  - GF_SERVER_SERVE_FROM_SUB_PATH=false
```

:::note Prometheus is not directly exposed in macOS local mode
Prometheus runs on the internal `backend-network` and is not bound to a host port in `docker-compose.local.yml`. All Prometheus data is accessible through Grafana. The `zyra-up.sh validate` command probes Prometheus from inside the container via `docker exec`.
:::

---

## Common macOS Issues

### Port 8082 / 8080 conflict

The API is mapped to host port `8082` in `docker-compose.local.yml` specifically to avoid conflicts with macOS system services (AirPlay Receiver, Control Center) that commonly bind `8080`. If port `8082` is also in use:

```bash
# Identify the conflicting process
lsof -nP -iTCP:8082 -sTCP:LISTEN

# Terminate it (replace <PID>)
kill -9 <PID>

# Then restart the stack
./zyra-up.sh start
```

### Port 3000 conflict

Port `3000` is commonly used by development servers (Next.js, React, etc.). If `zyrabit-web` fails to bind:

```bash
lsof -nP -iTCP:3000 -sTCP:LISTEN
```

Stop the conflicting process before starting Zyrabit. Alternatively, modify the host-side port binding in `zyrabit-slm/docker-compose.local.yml` (for example, change `3000:80` to `3002:80`) and update your browser bookmark accordingly.

### Docker Desktop is not running

`zyra-up.sh` will exit early with:

```
✖ Docker daemon is not running.
```

Open Docker Desktop from `/Applications` and wait for the whale icon in the menu bar to reach a steady state (not animating) before re-running the script.

### Ollama is not started or not responding

If `zyra-up.sh doctor` reports:

```
⚠ Local Ollama not detected on host. Will use Docker container.
```

The script falls back to attempting to start the `zyrabit-engine` Docker container, which is commented out in `docker-compose.local.yml`, causing startup to fail. Ensure Ollama is running:

```bash
# Probe Ollama directly
curl -s -m 2 http://127.0.0.1:11434/api/tags

# If not responding, launch the app
open -a Ollama
```

Wait a few seconds after launch, verify the probe returns a JSON response, then re-run `./zyra-up.sh start`.

### Required model not found in Ollama

If the API returns a model-not-found error on the first chat request:

```bash
# List locally available models
ollama list

# Pull the model configured in .env (default: qwen2.5:7b)
ollama pull qwen2.5:7b

# Pull the embedding model
ollama pull mxbai-embed-large
```

### `zyrabit-api` container exits immediately

Check logs for startup errors:

```bash
docker logs zyrabit-api --tail 50
```

Common causes on macOS:
- `.env` file is missing — run `cp zyrabit-slm/example.env zyrabit-slm/.env`.
- `zyrabit-db` (ChromaDB) is not yet healthy — wait 30–60 seconds and retry `./zyra-up.sh start`.
- Docker Desktop memory limit is too low — increase to at least 4 GB in **Settings -> Resources -> Memory**.

---

## Running the Test Suite

The unit test suite runs entirely offline. No running containers, no Ollama connection, and no network access are required. If a test reaches the network, that is considered a bug.

```bash
# From the repository root
uv run pytest -q zyrabit-slm/api-rag/tests/unit
```

The unit tests are located in:

```
zyrabit-slm/api-rag/tests/unit/
├── test_adapters.py
├── test_chat_logic.py
└── test_chat_use_case.py
```

All tests run against mocked dependencies and verify domain logic in isolation. `pytest.ini` configures `asyncio_mode = auto`, so async test functions execute without additional decorators.

To run the full validation suite (requires a running stack):

```bash
# Basic validation: unit tests + clean architecture check
./zyra-up.sh validate

# Full E2E security pipeline: PII check + air-gap verification + memory monitor (60s)
./zyra-up.sh validate --e2e-security
```

---

## Quick Reference

```bash
# First-time install (build images, start, pull models)
./zyra-up.sh install

# Start the stack (no model pull)
./zyra-up.sh start

# Stop the stack
./zyra-up.sh stop

# Health check (containers + API)
./zyra-up.sh verify

# System diagnostics (hardware, Docker, Ollama)
./zyra-up.sh doctor

# Continuous Watchdog diagnostic loop & trace watcher
./zyra-up.sh watch

# Run unit tests (fully offline)
uv run pytest -q zyrabit-slm/api-rag/tests/unit

# Run full validation suite
./zyra-up.sh validate --e2e-security

# Native dev mode (hot-reload via uv, no Docker for API)
./zyra-up.sh dev
```
