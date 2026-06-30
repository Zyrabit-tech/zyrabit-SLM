"""Port definition for connecting to MCP servers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class McpClientPort(ABC):
    """Provider-agnostic MCP Client contract."""

    @abstractmethod
    async def get_tools(self) -> List[Dict[str, Any]]:
        """Fetch available tools from the MCP server."""

    @abstractmethod
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool on the MCP server and return the result."""
