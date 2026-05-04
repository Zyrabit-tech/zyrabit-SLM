import os
import subprocess
import logging
from fastapi import FastAPI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

try:
    from fastmcp import FastMCP  # Preferred: standalone package
except ImportError:
    from mcp.server.fastmcp import FastMCP  # Fallback: official MCP SDK

# ── MCP Server Definition ───────────────────────────────────────────────────
mcp = FastMCP("Zyrabit Installer Agent")


@mcp.resource("docs://install-guide")
def get_install_guide() -> str:
    """
    Returns the Zyrabit installation guide from mounted README and CONTRIBUTING files.
    Used by AI agents (Claude, Cursor) to provide context-aware deployment assistance.
    """
    content = ""
    # Paths checked in order: Docker container paths first, then local fallbacks
    paths = [
        "/app/README.md",
        "/app/CONTRIBUTING_EN.md",
        "../README.md",
        "../CONTRIBUTING_EN.md",
    ]
    for path in paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content += f"\n# {os.path.basename(path)}\n" + f.read() + "\n"
            except Exception as e:
                logger.warning("Could not read install guide file '%s': %s", path, e)

    if not content:
        content = "Installation guide files not found. Ensure README.md is mounted at /app/README.md."
    return content


@mcp.tool()
def check_system_status() -> str:
    """
    Checks basic system health (disk space and memory) without requiring Docker daemon access.
    Safe to run in any environment.
    """
    results = []
    try:
        disk = subprocess.check_output(["df", "-h", "/app"], stderr=subprocess.DEVNULL).decode()
        results.append(f"Disk:\n{disk}")
    except Exception as e:
        results.append(f"Disk check failed: {e}")

    try:
        mem = subprocess.check_output(["free", "-m"], stderr=subprocess.DEVNULL).decode()
        results.append(f"Memory:\n{mem}")
    except Exception:
        # free is not available on macOS — skip gracefully
        results.append("Memory: check not available on this platform.")

    return "\n".join(results)


@mcp.tool()
def suggest_fix(error_query: str) -> str:
    """
    Returns a recommended fix based on the error description provided.
    Useful for AI agents diagnosing Zyrabit container or runtime issues.
    """
    q = error_query.lower()

    if "ionos" in q:
        return (
            "To deploy Zyrabit on an IONOS Cloud server:\n"
            "1. Provision a Cloud Server with Ubuntu 24.04 LTS.\n"
            "2. In the IONOS DCD Firewall Manager, open TCP ports 443 (Traefik) and 8001 (MCP API).\n"
            "3. SSH in and run: apt update && apt install docker.io docker-compose-v2\n"
            "4. Clone the repo and start with: docker compose up -d\n"
            "   Tip: If no GPU is available, use native CPU mode in docker-compose."
        )
    if "443" in q and "already in use" in q:
        return (
            "Port 443 is already in use. Stop any running Nginx, Apache, or other "
            "process occupying port 443 before starting the stack:\n"
            "  sudo lsof -i :443\n"
            "  sudo systemctl stop nginx"
        )
    if any(k in q for k in ["gpu", "cuda", "nvidia"]):
        return (
            "GPU initialization failed. Options:\n"
            "1. Switch to native Ollama mode by setting INFERENCE_PROVIDER=ollama_host in .env.\n"
            "2. Verify NVIDIA container runtime: docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi"
        )
    if "ollama:latest not found" in q or "image not found" in q:
        return (
            "Ollama image not found. Check your internet connection or pull manually:\n"
            "  docker pull ollama/ollama:latest"
        )
    if "exited" in q or "oom" in q or "out of memory" in q:
        return (
            "A container exited unexpectedly. Check logs for OOM or config errors:\n"
            "  docker compose logs zyrabit-api\n"
            "  docker compose logs zyrabit-engine\n"
            "If memory is the issue, switch to the quantized model: qwen2.5:1.5b"
        )
    if "uv" in q or "virtual environment" in q:
        return (
            "Dependency installation issue. Run from the repository root:\n"
            "  uv sync\n"
            "uv manages the virtualenv automatically — no manual venv creation needed."
        )

    return (
        "No specific fix found for this error. Check the README troubleshooting section "
        "or open an issue at https://github.com/Zyrabit-tech/zyrabit-SLM/issues"
    )


# ── HTTP / REST API ──────────────────────────────────────────────────────────
# The FastAPI app is used when running in --http mode (Docker container default).
# In stdio mode (Claude/Cursor desktop), only the MCP server is started.

app = FastAPI(
    title="Zyrabit MCP — Diagnostic API",
    description="HTTP interface to the Zyrabit Installer Agent MCP tools.",
    version="1.0.0",
)


class StatusResponse(BaseModel):
    status: str
    suggested_fix: str


@app.get("/diagnose", response_model=StatusResponse)
def diagnose_endpoint():
    """Returns system health status and a suggested fix if issues are detected."""
    status = check_system_status()
    status_lower = status.lower()

    if "exited" in status_lower or "oom" in status_lower:
        fix = suggest_fix("exited")
    elif "gpu" in status_lower or "error" in status_lower:
        fix = suggest_fix("gpu")
    else:
        fix = "All systems appear stable."

    return StatusResponse(status=status, suggested_fix=fix)


@app.get("/health")
def health():
    """Basic liveness probe for the MCP HTTP server."""
    return {"status": "ok", "server": "zyrabit-mcp"}


# ── Entrypoint ───────────────────────────────────────────────────────────────
import sys

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8001)
    else:
        # stdio mode: used by Claude Desktop, Cursor, and other MCP clients
        mcp.run()
