---
sidebar_position: 4
title: 'MCP Server & Model Selection'
description: 'Connect AI development tools to Zyrabit via the Model Context Protocol and configure inference models.'
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# MCP Server & Model Selection

The **Zyrabit MCP Bridge** (`zyrabit-mcp-bridge`) is a Model Context Protocol server that exposes Zyrabit's diagnostic tools, fix suggestions, and documentation resources to AI-powered development clients — including Claude Desktop, Cursor IDE, and autonomous agent frameworks. It acts as a structured, permission-controlled bridge between external AI tools and the Zyrabit stack running on your host or in Docker.

---

## Architecture Overview

```
┌──────────────────────────────────────────┐
│            AI Client Layer               │
│   Claude Desktop  │  Cursor IDE  │ Agent │
└────────────┬─────────────────────────────┘
             │  MCP (stdio or HTTP-JSONRPC)
             ▼
┌──────────────────────────────────────────┐
│         zyrabit-mcp  (container)         │
│   python install_server.py [--http]      │
│   Port 8001  │  Protocol: 2025-01-01     │
│   Whitelist enforced, no Docker socket   │
└────────────┬─────────────────────────────┘
             │  Internal Docker network
             ▼
┌──────────────────────────────────────────┐
│    zyrabit-engine  │  api-rag  │  nginx   │
│    Ollama inference│  PII data │  gateway │
└──────────────────────────────────────────┘
```

The MCP server does **not** have access to the Docker daemon socket. All sensitive retrieval-augmented generation (RAG) data and personally identifiable information remain isolated inside `api-rag`. The MCP layer exposes only the explicitly whitelisted commands and files described in [Security Model](#security-model).

---

## Protocol Configuration

The server is configured by `mcp/config.json`:

```json title="mcp/config.json"
{
  "protocolVersion": "2025-01-01",
  "server": {
    "name": "zyrabit-mcp-bridge",
    "version": "0.1.0"
  },
  "transport": {
    "type": "http-jsonrpc",
    "endpoint": "https://localhost/mcp"
  },
  "capabilities": {
    "tools": { "listChanged": false },
    "resources": { "subscribe": false, "listChanged": false },
    "prompts": { "listChanged": false }
  },
  "security": {
    "sanitization": "always-on",
    "allowedPathsEnv": "MCP_ALLOWED_PATHS"
  }
}
```

| Field | Value | Description |
|---|---|---|
| `protocolVersion` | `2025-01-01` | MCP specification revision |
| `server.name` | `zyrabit-mcp-bridge` | Identifier advertised to clients |
| `transport.type` | `http-jsonrpc` | Wire format in HTTP mode |
| `security.sanitization` | `always-on` | Input sanitisation is never disabled |
| `security.allowedPathsEnv` | `MCP_ALLOWED_PATHS` | Env var controlling readable paths |

---

## Execution Modes

The `zyrabit-mcp` container supports two mutually exclusive launch modes. The mode is determined by whether `--http` is passed to `install_server.py`.

### stdio Mode

Used by AI clients that spawn the server as a subprocess and communicate over standard input/output. This is the required mode for Claude Desktop and Cursor IDE.

```bash
python install_server.py
```

- Transport: `stdin` / `stdout`
- No listening port exposed
- Lifecycle managed by the client process

### HTTP Mode

Used for direct HTTP-JSONRPC access and is the default mode when the container is started by Docker Compose.

```bash
python install_server.py --http
```

- Binds to `0.0.0.0:8001` inside the container
- Exposed on the host as port `8001`
- Accepts JSON-RPC 2.0 POST requests at `/mcp`
- Health check available at `GET /health`

---

## Tool Reference

The following tools are registered with the MCP server and available to any connected client that authenticates with a valid `ZYRABIT_API_KEY_MCP` token.

### MCP Tools

| Tool | Signature | Description |
|---|---|---|
| `check_system_status` | `check_system_status()` | Returns current disk usage (`df -h /app`) and available RAM (`free -m`) from the host |
| `suggest_fix` | `suggest_fix(error_query: str)` | Accepts a free-text error description and returns a recommended remediation step |

### MCP Resources

| Resource URI | Description |
|---|---|
| `docs://install-guide` | Serves the content of `/app/README.md` and `/app/CONTRIBUTING.md` mounted read-only into the container, providing context-aware installation and contribution guidance to the AI client |

### REST Endpoints

These endpoints are available only when the server is running in **HTTP mode** on port `8001`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check; returns `{"status": "ok"}` when the server is running |
| `GET` | `/diagnose` | Runs `check_system_status` and returns a JSON summary of disk and memory state |

---

## Connecting to Claude Desktop

Claude Desktop communicates with the MCP server via **stdio mode** by invoking `docker exec` against the running `zyrabit-mcp` container.

### Prerequisites

- The Zyrabit stack must be running (`./zyra-up.sh start` or `docker compose up -d`).
- Docker must be accessible from the user account running Claude Desktop.

### Configuration

Add the following block to your `claude_desktop_config.json` file:

```json title="claude_desktop_config.json"
{
  "mcpServers": {
    "zyrabit-installer": {
      "command": "docker",
      "args": ["exec", "-i", "zyrabit-mcp", "python", "install_server.py"]
    }
  }
}
```

:::important
The `-i` flag keeps `stdin` open, which is required for MCP stdio transport. Omitting it will cause the connection to fail immediately.
:::

**File location by platform:**

| Platform | Path |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

After saving the file, **quit and restart Claude Desktop**. The `zyrabit-installer` server will appear in the MCP servers list. You can verify the connection by asking Claude: *"Use the zyrabit-installer to check system status."*

---

## Connecting to Cursor IDE

Cursor IDE supports MCP servers via its built-in server manager.

### Steps

1. Open **Cursor Settings** (`Cmd + ,` on macOS, `Ctrl + ,` on Windows/Linux).
2. Navigate to **Features → MCP Servers**.
3. Click **Add New MCP Server**.
4. Fill in the fields:

| Field | Value |
|---|---|
| **Name** | `zyrabit-installer` |
| **Type** | `command` |
| **Command** | `docker exec -i zyrabit-mcp python install_server.py` |

5. Click **Save**. Cursor will immediately attempt to connect and list available tools.

:::note
Cursor spawns the command in a subprocess with stdio transport, identical to the Claude Desktop integration. The `zyrabit-mcp` container must be running before Cursor attempts the connection.
:::

---

## Security Model

The MCP server enforces a strict permission boundary to prevent lateral movement across the Zyrabit stack.

### Command Whitelist

Only the following commands may be executed by any MCP tool call, as defined in `mcp/mcp-tools-whitelist.yml`:

| Command Name | Shell Command | Purpose |
|---|---|---|
| `check_disk_usage` | `df -h /app` | Verify available disk space for documents |
| `check_memory` | `free -m` | Verify available RAM for SLM inference |

Any tool invocation that attempts to execute a command not in this list is rejected before execution.

### File Access Whitelist

MCP resource access is restricted to the following paths:

```yaml title="mcp/mcp-tools-whitelist.yml (allowed_files)"
allowed_files:
  - "/app/README.md"
  - "/app/CONTRIBUTING.md"
  - "/app/config.json"
```

Both `/app/README.md` and `/app/CONTRIBUTING.md` are mounted into `zyrabit-mcp` as **read-only** volumes. Write operations to these paths are rejected at the container mount level.

### Isolation Guarantees

| Constraint | Detail |
|---|---|
| No Docker socket | `zyrabit-mcp` does not have `/var/run/docker.sock` mounted; it cannot spawn, inspect, or control other containers |
| No PII access | User documents and RAG embeddings reside exclusively in `api-rag`; `zyrabit-mcp` has no network route to `api-rag` data storage |
| Sanitisation | All inputs pass through `sanitization: always-on` before any command or file path is resolved |
| API key required | MCP clients must supply a valid `ZYRABIT_API_KEY_MCP` token; unauthenticated requests are rejected at the server boundary |

---

## HTTP Endpoint Examples

When the stack is running with `zyrabit-mcp` in HTTP mode (default via Docker Compose), you can interact with the REST interface directly.

### Health Check

```bash
curl -s http://localhost:8001/health
```

**Expected response:**

```json
{"status": "ok"}
```

### Diagnose System

```bash
curl -s http://localhost:8001/diagnose \
  -H "Authorization: Bearer $ZYRABIT_API_KEY_MCP"
```

**Expected response (example):**

```json
{
  "disk": {
    "filesystem": "/dev/sda1",
    "size": "50G",
    "used": "12G",
    "available": "38G",
    "use_percent": "24%",
    "mounted_on": "/app"
  },
  "memory": {
    "total_mb": 16384,
    "used_mb": 7200,
    "free_mb": 9184
  }
}
```

### MCP JSON-RPC: Call `check_system_status`

```bash
curl -s -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ZYRABIT_API_KEY_MCP" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "check_system_status",
      "arguments": {}
    }
  }'
```

### MCP JSON-RPC: Call `suggest_fix`

```bash
curl -s -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ZYRABIT_API_KEY_MCP" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "suggest_fix",
      "arguments": {
        "error_query": "Ollama container exits with OOM error during model load"
      }
    }
  }'
```

---

## Model Selection

Zyrabit uses [Ollama](https://ollama.com) for local SLM inference. The active model is determined at stack startup and can be changed without rebuilding images.

### Automatic Model Detection

At install time, `zyra-up.sh` detects available system RAM and selects a default model automatically:

| Available RAM | Default Model | Notes |
|---|---|---|
| ≥ 12 GB | `qwen2.5:7b` | Recommended for production and general use |
| < 12 GB | `qwen2.5:1.5b` | Reduced-parameter model for memory-constrained hosts |

The embedding model is always `mxbai-embed-large`, regardless of available RAM.

### Environment Variable Configuration

The active model is controlled by the `MODEL_NAME` variable in your `.env` file:

```bash title=".env"
MODEL_NAME=qwen2.5:7b
INFERENCE_PROVIDER=ollama
```

#### `INFERENCE_PROVIDER` Options

| Value | Description |
|---|---|
| `ollama` | Ollama running inside the `zyrabit-engine` container (default) |
| `ollama_host` | Ollama running on the Docker host, accessed via `host.docker.internal` |
| `ollama_docker` | Ollama in a separate Docker container on the same network |
| `openai_compatible` | Any OpenAI-compatible API endpoint (set `OPENAI_API_BASE` accordingly) |

### Supported Models

Any model available in the [Ollama library](https://ollama.com/library) can be used. The following have been validated with Zyrabit:

| Model | `MODEL_NAME` value | Minimum RAM | Best For |
|---|---|---|---|
| Qwen 2.5 7B | `qwen2.5:7b` | 12 GB | General purpose, default |
| Qwen 2.5 1.5B | `qwen2.5:1.5b` | 4 GB | Low-resource deployments |
| Llama 3 | `llama3` | 8 GB | General purpose |
| Mistral | `mistral` | 8 GB | Instruction following |
| Code Llama | `codellama` | 8 GB | Code generation and review |
| Phi-3 | `phi3` | 4 GB | Lightweight, fast inference |

:::tip
For code-heavy workloads such as reviewing pull requests or explaining stack traces, `codellama` or `qwen2.5:7b` typically outperforms the smaller variants.
:::

### Embedding Model

The embedding model is fixed at `mxbai-embed-large` and is used exclusively by `api-rag` for document indexing. It is not affected by `MODEL_NAME`.

---

## Changing the Model

### Method 1: Override at Install Time

Pass `--model` to `zyra-up.sh` to pull and activate a model in a single step:

```bash
./zyra-up.sh install --model mistral
```

This pulls the model into `zyrabit-engine` via Ollama and writes `MODEL_NAME=mistral` to `.env`.

### Method 2: Update `.env` and Restart

1. Edit `.env` and set the desired model:

   ```bash
   MODEL_NAME=codellama
   ```

2. Restart only the affected services:

   ```bash
   docker compose up -d zyrabit-engine api-rag
   ```

### Method 3: Pull a Model Manually

Pull a new model into the running `zyrabit-engine` container without changing the default:

```bash
docker exec -it zyrabit-engine ollama pull codellama
```

The model is immediately available for inference but will not be used until `MODEL_NAME` is updated and the services are restarted.

---

## Testing a Model Change End-to-End

The following procedure validates that a model change propagates correctly through the stack.

**1. Pull the new model:**

```bash
docker exec -it zyrabit-engine ollama pull mistral
```

**2. Update `.env`:**

```bash
# Replace the existing MODEL_NAME line
sed -i '' 's/^MODEL_NAME=.*/MODEL_NAME=mistral/' .env
```

**3. Restart inference and RAG services:**

```bash
docker compose up -d zyrabit-engine api-rag
```

**4. Confirm the model is loaded:**

```bash
docker exec -it zyrabit-engine ollama list
```

The output should include `mistral` in the model list.

**5. Verify the MCP bridge reports a healthy system:**

```bash
curl -s http://localhost:8001/health
```

Expected: `{"status": "ok"}`

**6. Send a test inference request through MCP:**

```bash
curl -s -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ZYRABIT_API_KEY_MCP" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "suggest_fix",
      "arguments": {
        "error_query": "Model not found: qwen2.5:7b"
      }
    }
  }'
```

A well-formed JSON response with a `result` field confirms the new model (`mistral`) is serving inference requests through the MCP bridge.

:::warning
Do not change `MODEL_NAME` while a RAG ingestion job is running. Switching models mid-ingestion will produce embedding mismatches in the vector store and will require a full re-ingestion of documents.
:::
