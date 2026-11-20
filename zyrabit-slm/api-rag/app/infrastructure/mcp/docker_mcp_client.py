"""
Docker MCP Integration - Strictly Read-Only.
Allows the Zyrabit SLM to diagnose local containers, read logs, and check status.

Access is constrained by:
1. DOCKER_HOST (compose routes via docker-socket-proxy; CONTAINERS read-only)
2. DOCKER_MCP_CONTAINER_ALLOWLIST (fnmatch patterns; default zyrabit-*)
"""

from __future__ import annotations

import fnmatch
import logging
import os
from typing import Any, Dict, List, Optional

import docker

logger = logging.getLogger("zyrabit.mcp.docker")

_DEFAULT_ALLOWLIST = "zyrabit-*"


def parse_container_allowlist(raw: Optional[str] = None) -> List[str]:
    """Parse a comma-separated allowlist of container name patterns (fnmatch)."""
    value = _DEFAULT_ALLOWLIST if raw is None else raw
    patterns = [part.strip() for part in value.split(",") if part.strip()]
    return patterns or [_DEFAULT_ALLOWLIST]


def container_name_allowed(name: str, allowlist: List[str]) -> bool:
    """Return True when the container name matches at least one allowlist pattern."""
    normalized = name.lstrip("/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in allowlist)


class DockerDiagnosticClient:
    """Client for retrieving Docker diagnostics securely (Read-Only + allowlist)."""

    def __init__(self, allowlist: Optional[List[str]] = None):
        self.allowlist = allowlist if allowlist is not None else parse_container_allowlist(
            os.getenv("DOCKER_MCP_CONTAINER_ALLOWLIST")
        )
        try:
            self.client = docker.from_env()
        except Exception as e:
            logger.warning(f"Could not connect to Docker daemon: {e}")
            self.client = None

    def _check_client(self):
        if not self.client:
            raise RuntimeError("Docker client is not connected. Ensure Docker is running and accessible.")

    def _deny_message(self, container_name: str) -> str:
        return (
            f"Error: Container '{container_name}' is not in DOCKER_MCP_CONTAINER_ALLOWLIST "
            f"({', '.join(self.allowlist)})."
        )

    def list_containers(self) -> List[Dict[str, Any]]:
        """List allowlisted containers (running and stopped)."""
        self._check_client()
        try:
            containers = self.client.containers.list(all=True)
            result = []
            for c in containers:
                if not container_name_allowed(c.name, self.allowlist):
                    continue
                result.append({
                    "id": c.short_id,
                    "name": c.name,
                    "status": c.status,
                    "image": c.image.tags[0] if c.image.tags else "unknown"
                })
            return result
        except Exception as e:
            return [{"error": str(e)}]

    def get_container_logs(self, container_name: str, tail: int = 50) -> str:
        """Get the latest logs for a specific allowlisted container."""
        self._check_client()
        if not container_name_allowed(container_name, self.allowlist):
            return self._deny_message(container_name)
        try:
            container = self.client.containers.get(container_name)
            logs = container.logs(tail=tail, stdout=True, stderr=True)
            return logs.decode('utf-8', errors='replace')
        except docker.errors.NotFound:
            return f"Error: Container '{container_name}' not found."
        except Exception as e:
            return f"Error reading logs: {str(e)}"

    def inspect_container(self, container_name: str) -> Dict[str, Any]:
        """Inspect an allowlisted container for health, ports, and state."""
        self._check_client()
        if not container_name_allowed(container_name, self.allowlist):
            return {"error": self._deny_message(container_name)}
        try:
            container = self.client.containers.get(container_name)
            attrs = container.attrs
            return {
                "name": attrs.get("Name"),
                "state": attrs.get("State"),
                "restart_count": attrs.get("RestartCount"),
                "network": attrs.get("NetworkSettings", {}).get("Ports", {})
            }
        except docker.errors.NotFound:
            return {"error": f"Container '{container_name}' not found."}
        except Exception as e:
            return {"error": str(e)}

# Singleton instance
docker_client = DockerDiagnosticClient()
