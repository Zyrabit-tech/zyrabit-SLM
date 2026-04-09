from fastapi import APIRouter, Response
from typing import Dict, Any
from app.domain.services.mcp_service import handle_jsonrpc, get_config

router = APIRouter()

@router.get("/config.json")
async def mcp_config():
    """Dynamic MCP configuration discovery."""
    return get_config()

@router.post("")
async def mcp_rpc(payload: Dict[str, Any]):
    """JSON-RPC endpoint for MCP tools and resources."""
    result, status_code = handle_jsonrpc(payload)
    return Response(content=str(result).replace("'", '"'), media_type="application/json", status_code=status_code)
