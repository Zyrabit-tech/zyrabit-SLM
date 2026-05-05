# Zyrabit MCP — Installer Agent

An MCP (Model Context Protocol) server that acts as an automated technical assistant for deploying and diagnosing the Zyrabit SLM ecosystem.

---

## What it does

| Capability | Description |
|---|---|
| `docs://install-guide` (resource) | Serves the README and CONTRIBUTING guide to MCP clients for context-aware assistance |
| `check_system_status` (tool) | Returns disk and memory health of the host without requiring Docker daemon access |
| `suggest_fix` (tool) | Returns a recommended fix based on a plain-text error description |
| `GET /diagnose` (HTTP) | REST endpoint combining status + fix suggestion for generic HTTP consumers |
| `GET /health` (HTTP) | Liveness probe for container health checks |

---

## Two execution modes

| Mode | How to start | Used by |
|---|---|---|
| **stdio** | `python install_server.py` | Claude Desktop, Cursor, AI agents |
| **HTTP** | `python install_server.py --http` | Docker container (port 8001), REST clients |

---

## Connecting to AI Clients

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "zyrabit-installer": {
      "command": "docker",
      "args": ["exec", "-i", "zyrabit-mcp", "python", "install_server.py"]
    }
  }
}
```

> Make sure the `zyrabit-mcp` container is running (`./zyra-up.sh start`).

### Cursor IDE

Go to **Settings → Features → MCP Servers** and add:

- **Type:** `command`
- **Name:** `Zyrabit Installer`
- **Command:** `docker exec -i zyrabit-mcp python install_server.py`

Or, to run without Docker (local dev):

- **Command:** `python path/to/mcp/install_server.py`

---

## HTTP Endpoints

When running in `--http` mode (default in Docker):

```bash
# Health check
curl http://localhost:8001/health
# → {"status":"ok","server":"zyrabit-mcp"}

# Diagnostic report
curl http://localhost:8001/diagnose
# → {"status":"Disk: ...", "suggested_fix":"All systems appear stable."}
```

---

## Tools Reference

### `check_system_status`

Returns disk usage (at `/app`) and available memory. Safe to call in any environment — gracefully skips checks that are unavailable on the current platform (e.g. `free` on macOS).

### `suggest_fix(error_query: str)`

Accepts a plain-text error description and returns an actionable recommendation.

Recognized patterns:

| Error keyword | What it suggests |
|---|---|
| `ionos` | IONOS Cloud deployment steps |
| `443`, `already in use` | Stop conflicting process on port 443 |
| `gpu`, `cuda`, `nvidia` | Switch to native Ollama or verify container runtime |
| `ollama:latest not found` | Pull the image manually |
| `exited`, `oom`, `out of memory` | Check logs, reduce model size |
| `uv`, `virtual environment` | Run `uv sync` from repo root |

---

## Security

- The server does not expose Docker socket access by default.
- `check_system_status` uses only `df` and `free` — no shell injection vectors.
- File access is limited to paths defined in `mcp-tools-whitelist.yml`.
- PII sanitization is **not** the responsibility of this server — that lives in `api-rag`.

---

## Files

| File | Purpose |
|---|---|
| `install_server.py` | MCP server + FastAPI HTTP app |
| `config.json` | Static MCP capability declaration (served by `api-rag` at `/mcp/config.json`) |
| `mcp-tools-whitelist.yml` | Allowed system commands and file paths |
| `Dockerfile` | Multi-stage image for the MCP container |
| `requirements.txt` | Python dependencies for this service |
