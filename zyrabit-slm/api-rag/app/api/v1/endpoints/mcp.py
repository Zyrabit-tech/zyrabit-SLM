import json
from fastapi import APIRouter, Response, Request
from typing import Dict, Any
from app.domain.services.mcp_service import mcp

router = APIRouter()

@router.get("/config.json")
async def mcp_config():
    """Dynamic MCP configuration discovery."""
    return {
        "mcp_server": "Zyrabit Sovereign Core",
        "version": "1.0.0",
        "capabilities": ["tools"]
    }

@router.post("/rpc")
async def mcp_rpc(request: Request):
    """JSON-RPC bridge to the Native FastMCP instance."""
    payload = await request.json()
    method = payload.get("method")
    params = payload.get("params", {})
    rpc_id = payload.get("id")

    # 1. LIST TOOLS
    if method == "tools/list":
        tools = [{"name": t.name, "description": t.description, "inputSchema": t.parameters} for t in mcp._tool_manager._tools.values()]
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {"tools": tools}
        }
    
    # 2. CALL TOOL
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in mcp._tool_manager._tools:
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"}
            }
        
        try:
            # Execute the tool via FastMCP ToolManager
            result = await mcp._tool_manager.call_tool(tool_name, arguments)
            
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "result": {
                    "content": [{"type": "text", "text": str(result)}]
                }
            }
        except Exception as e:
            logger.exception("Error while calling MCP tool '%s'", tool_name)
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": -32000, "message": "Internal server error"}
            }


    
    return {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "error": {"code": -32601, "message": "Method not found in bridge"}
    }
