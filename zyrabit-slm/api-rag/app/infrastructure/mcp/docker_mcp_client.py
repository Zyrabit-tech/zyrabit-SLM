"""
Docker MCP Integration - Strictly Read-Only.
Allows the Zyrabit SLM to diagnose local containers, read logs, and check status.
"""

import logging
import docker
from typing import Dict, List, Any

logger = logging.getLogger("zyrabit.mcp.docker")


class DockerDiagnosticClient:
    """Client for retrieving Docker diagnostics securely (Read-Only)."""

    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            logger.warning(f"Could not connect to Docker daemon: {e}")
            self.client = None

    def _check_client(self):
        if not self.client:
            raise RuntimeError("Docker client is not connected. Ensure Docker is running and accessible.")

    def list_containers(self) -> List[Dict[str, Any]]:
        """List all containers (running and stopped)."""
        self._check_client()
        try:
            containers = self.client.containers.list(all=True)
            result = []
            for c in containers:
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
        """Get the latest logs for a specific container."""
        self._check_client()
        try:
            container = self.client.containers.get(container_name)
            logs = container.logs(tail=tail, stdout=True, stderr=True)
            return logs.decode('utf-8', errors='replace')
        except docker.errors.NotFound:
            return f"Error: Container '{container_name}' not found."
        except Exception as e:
            return f"Error reading logs: {str(e)}"

    def inspect_container(self, container_name: str) -> Dict[str, Any]:
        """Inspect a container for health, ports, and state."""
        self._check_client()
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

