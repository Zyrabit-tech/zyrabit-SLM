"""Adapter for interacting with MCP servers."""

from __future__ import annotations

import logging
from typing import List, Dict, Any

from app.domain.ports.mcp_client_port import McpClientPort
from app.domain.services.mcp_service import mcp

logger = logging.getLogger("zyrabit.mcp.client")

class InternalMcpClientAdapter(McpClientPort):
    """Adapter that connects directly to the embedded FastMCP instance."""

    async def get_tools(self) -> List[Dict[str, Any]]:
        """Fetch available tools from the embedded MCP server."""
        try:
            tools = []
            for t in mcp._tool_manager._tools.values():
                tools.append({
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.parameters
                })
            return tools
        except Exception as e:
            logger.error(f"Failed to fetch tools from MCP: {e}")
            return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool on the embedded MCP server."""
        try:
            if name not in mcp._tool_manager._tools:
                raise ValueError(f"Tool {name} not found in MCP server.")
            logger.info(f"🛠️ Executing MCP Tool: {name} with args {arguments}")
            return await mcp._tool_manager.call_tool(name, arguments)
        except Exception as e:
            logger.error(f"Error executing MCP tool {name}: {e}")
            return f"Error executing tool {name}: {e}"
