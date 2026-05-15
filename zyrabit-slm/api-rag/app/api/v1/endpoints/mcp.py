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
    # FastMCP uses its own ASGI handler, but we can call it manually
    # or just let the app mount handle it. For now, we bridge the post.
    payload = await request.json()
    
    # Simple bridge for the UI which expects /v1/rpc
    # We can use the mcp instance to handle the JSON-RPC call
    # Note: FastMCP usually handles this via its ASGI app at a mount point.
    # To keep it simple for the UI, we'll keep this endpoint for now.
    
    # We'll return the tool list if requested, which is what the UI does.
    if payload.get("method") == "tools/list":
        tools = [{"name": t.name, "description": t.description} for t in mcp._tools.values()]
        return {
            "jsonrpc": "2.0",
            "id": payload.get("id"),
            "result": {"tools": tools}
        }
    
    return {
        "jsonrpc": "2.0",
        "id": payload.get("id"),
        "error": {"code": -32601, "message": "Method not found in bridge"}
    }
