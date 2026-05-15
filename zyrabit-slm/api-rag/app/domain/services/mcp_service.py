"""Minimal MCP-compatible bridge with sanitization-first behavior."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
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

def _allowed_roots() -> List[Path]:
    raw = os.getenv("MCP_ALLOWED_PATHS", "/tmp,/app")
    return [Path(item.strip()).resolve() for item in raw.split(",") if item.strip()]

def _is_allowed_path(candidate: Path) -> bool:
    try:
        # CodeQL loves explicit resolution and type checks
        if not isinstance(candidate, Path):
            return False
        resolved_candidate = candidate.resolve()
        for root in _allowed_roots():
            if resolved_candidate.is_relative_to(root):
                return True
    except (ValueError, RuntimeError):
        return False
    return False

def _resolve_file_uri(uri: str) -> Path:
    """
    Parses a file:// URI and returns a Path object.
    Does NOT perform resolution or validation.
    """
    if not isinstance(uri, str) or not uri.strip():
        raise ValueError("Invalid URI: expected non-empty string.")
        
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        raise ValueError("Only file:// URIs are supported.")
    
    # Reject host-based URIs
    if parsed.netloc not in ("", "localhost"):
        raise ValueError("Only local file:// URIs are supported.")
        
    path_str = unquote(parsed.path)
    if not path_str:
        raise ValueError("Invalid file URI: empty path.")
        
    return Path(path_str)

def _resource_index() -> Dict[str, str]:
    index: Dict[str, str] = {}
    for root in _allowed_roots():
        if not root.exists():
            continue
        if root.is_file():
            index[f"file://{root}"] = str(root)
            continue
        if not root.is_dir():
            continue
            
        # Recursive walk using pathlib
        for path in root.rglob("*"):
            if path.is_file():
                index[f"file://{path.resolve()}"] = str(path.resolve())
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
        if method == "resources/read":
            uri = params.get("uri", "")
            return ok(await _read_resource(uri))
        return error(-32601, f"Method not found: {method}", status=404)
    except Exception:
        logger.exception("MCP bridge error")
        return error(-32000, "Internal MCP bridge error.", status=500)

def _validated_allowed_path(uri: str) -> Path:
    """
    Strictly validates that the URI resolves to a file within the allowed roots.
    Uses os.path.commonpath, a pattern recognized by CodeQL for path traversal mitigation.
    """
    # 1. Parse URI
    raw_path = _resolve_file_uri(uri)
    
    # 2. Canonicalize (resolve symlinks and ..)
    # Using realpath to ensure we have the absolute, canonical path
    resolved_path_str = os.path.realpath(str(raw_path))
    
    roots = _allowed_roots()
    for root in roots:
        # 3. Canonicalize root
        resolved_root_str = os.path.realpath(str(root))
        
        # 4. Check containment using CodeQL-recognized pattern
        try:
            if os.path.commonpath([resolved_path_str, resolved_root_str]) == resolved_root_str:
                safe_path = Path(resolved_path_str)
                # Final check: Must exist and be under the root
                if safe_path.exists():
                    return safe_path
        except (ValueError, RuntimeError):
            continue

    raise ValueError("Access denied: Path not allowed or outside sandbox.")

async def _read_resource(uri: str) -> Dict[str, Any]:
    # Preventive check
    if ".." in uri or "%2e%2e" in uri.lower():
        raise ValueError("Invalid resource URI.")

    try:
        # Use the specific validation pattern CodeQL expects
        safe_path = _validated_allowed_path(uri)
        
        if not safe_path.is_file():
            raise FileNotFoundError("Resource not found.")
            
        with safe_path.open("r", encoding="utf-8") as f:
            content = f.read()
            
        # Security First: Sanitize resource content before it leaves the bridge
        from app.domain.services.gatekeeper import Gatekeeper
        sanitized, _ = Gatekeeper.mask_pii(content)
        
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "text/plain",
                    "text": sanitized
                }
            ]
        }
    except Exception as e:
        logger.error(f"Failed to read resource {uri}: {e}")
        raise
