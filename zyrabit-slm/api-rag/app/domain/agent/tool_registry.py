"""
ToolRegistry — Manages MCP tools discovery and execution in the domain layer.
"""
from typing import Dict, Any, List
import logging
from app.domain.ports.mcp_client_port import McpClientPort

logger = logging.getLogger("zyrabit.agent.registry")


class ToolRegistry:
    """
    Registry that dynamically discovers internal/external tools via McpClientPort
    and provides execution interfaces for the ReAct loop.
    """

    def __init__(self, mcp_client: McpClientPort) -> None:
        self.mcp_client = mcp_client

    async def get_tools_definition(self) -> List[Dict[str, Any]]:
        """Fetch all available tool schemas (FastMCP format)."""
        if not self.mcp_client:
            return []
        try:
            return await self.mcp_client.get_tools()
        except Exception as e:
            logger.error(f"Failed to fetch tool definitions: {e}")
            return []

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call the tool via the configured client adapter."""
        if not self.mcp_client:
            return f"Error: Tool registry has no configured client to execute {name}."
        try:
            return await self.mcp_client.call_tool(name, arguments)
        except Exception as e:
            logger.error(f"Error during execution of {name}: {e}")
            return f"Error executing tool {name}: {e}"
