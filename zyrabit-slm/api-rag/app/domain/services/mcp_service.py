"""Minimal MCP-compatible bridge with sanitization-first behavior."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Tuple
from urllib.parse import unquote, urlparse

# Global state access
_app_state = None

def set_mcp_app_state(state):
    global _app_state
    _app_state = state

MCP_PROTOCOL_VERSION = "2025-01-01"
MCP_SERVER_NAME = "zyrabit-mcp-bridge"
MCP_SERVER_VERSION = "0.1.0"
logger = logging.getLogger("zyrabit.api")

def _allowed_roots() -> List[str]:
    raw = os.getenv("MCP_ALLOWED_PATHS", "/tmp,/app")
    return [os.path.abspath(item.strip()) for item in raw.split(",") if item.strip()]

def _is_allowed_path(candidate: str) -> bool:
    path = os.path.abspath(candidate)
    for root in _allowed_roots():
        if path == root or path.startswith(root + os.sep):
            return True
    return False

def _resolve_file_uri(uri: str) -> str:
    parsed = urlparse(uri)
    if parsed.scheme not in ("file", ""):
        raise ValueError("Only file:// URIs are supported.")
    path = unquote(parsed.path if parsed.scheme == "file" else uri)
    return os.path.abspath(path)

def _resource_index() -> Dict[str, str]:
    index: Dict[str, str] = {}
    for root in _allowed_roots():
        if os.path.isfile(root):
            abs_path = os.path.abspath(root)
            index[f"file://{abs_path}"] = abs_path
            continue
        if not os.path.isdir(root):
            continue
        for current_root, _, files in os.walk(root):
            for filename in files:
                abs_path = os.path.abspath(os.path.join(current_root, filename))
                index[f"file://{abs_path}"] = abs_path
    return index

def get_config() -> Dict[str, Any]:
    return {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "server": {"name": MCP_SERVER_NAME, "version": MCP_SERVER_VERSION},
        "transport": {"type": "http-jsonrpc", "endpoint": "/mcp"},
        "capabilities": {
            "tools": {"listChanged": False},
            "resources": {"subscribe": False, "listChanged": False},
            "prompts": {"listChanged": False},
        },
        "security": {
            "sanitization": "always-on",
            "allowedPaths": _allowed_roots(),
        },
    }

def list_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "secure_chat",
            "description": "Send a prompt through Zyrabit RAG pipeline and return response.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "sanitize_text",
            "description": "Anonymize text using Zyrabit Gatekeeper.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                },
                "required": ["text"],
            },
        }
    ]

async def _tool_secure_chat(arguments: Dict[str, Any]) -> Dict[str, Any]:
    prompt = str(arguments.get("prompt", ""))
    if not _app_state or not hasattr(_app_state, 'chat_use_case'):
        return {"content": [{"type": "text", "text": "Error: Chat engine not ready."}]}
    
    result = await _app_state.chat_use_case.execute(text=prompt)
    return {
        "content": [{"type": "text", "text": result.get("response", "")}],
        "metadata": result.get("metadata", {}),
    }

async def _tool_sanitize_text(arguments: Dict[str, Any]) -> Dict[str, Any]:
    text = str(arguments.get("text", ""))
    if not _app_state: return {"error": "State not ready"}
    
    # Use the Gatekeeper directly
    from app.domain.services.gatekeeper import Gatekeeper
    sanitized, entities = Gatekeeper.mask_pii(text)
    return {
        "content": [{"type": "text", "text": sanitized}],
        "metadata": {"detectedEntities": entities},
    }

async def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "secure_chat":
        return await _tool_secure_chat(arguments)
    if name == "sanitize_text":
        return await _tool_sanitize_text(arguments)
    raise ValueError(f"Unknown tool: {name}")

async def handle_jsonrpc(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})

    def ok(result: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }, 200

    def error(code: int, message: str, status: int = 400) -> Tuple[Dict[str, Any], int]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }, status

    try:
        if method == "initialize":
            return ok({
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "serverInfo": {"name": MCP_SERVER_NAME, "version": MCP_SERVER_VERSION},
                "capabilities": get_config()["capabilities"],
            })
        if method == "tools/list":
            return ok({"tools": list_tools()})
        if method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            return ok(await call_tool(name=name, arguments=arguments))
        return error(-32601, f"Method not found: {method}", status=404)
    except Exception as exc:
        logger.exception("MCP bridge error")
        return error(-32000, "Internal MCP bridge error.", status=500)
