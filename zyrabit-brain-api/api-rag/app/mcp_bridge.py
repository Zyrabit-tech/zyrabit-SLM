"""Minimal MCP-compatible bridge with sanitization-first behavior."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple
from urllib.parse import unquote, urlparse

from .security import anonymize_text
from .services import query_secure_slm


MCP_PROTOCOL_VERSION = "2025-01-01"
MCP_SERVER_NAME = "zyrabit-mcp-bridge"
MCP_SERVER_VERSION = "0.1.0"


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
            "description": "Send a prompt through Zyrabit secure pipeline and return response.",
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
            "description": "Anonymize text and return tokenized output.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                },
                "required": ["text"],
            },
        },
        {
            "name": "read_local_resource",
            "description": "Read local file content (allowed roots only), sanitized by default.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "uri": {"type": "string"},
                    "sanitize": {"type": "boolean", "default": True},
                },
                "required": ["uri"],
            },
        },
    ]


def list_resources() -> List[Dict[str, Any]]:
    return [
        {
            "uri": "file:///tmp",
            "name": "tmp-root",
            "description": "Temporary directory (example allowed root).",
            "mimeType": "text/plain",
        }
    ]


def _tool_secure_chat(arguments: Dict[str, Any]) -> Dict[str, Any]:
    prompt = str(arguments.get("prompt", ""))
    response, latency = query_secure_slm(prompt)
    return {
        "content": [{"type": "text", "text": response}],
        "metadata": {"latencySeconds": latency},
    }


def _tool_sanitize_text(arguments: Dict[str, Any]) -> Dict[str, Any]:
    text = str(arguments.get("text", ""))
    result = anonymize_text(text)
    return {
        "content": [{"type": "text", "text": result.sanitized_text}],
        "metadata": {"detectedEntities": result.detected_entities},
    }


def _tool_read_local_resource(arguments: Dict[str, Any]) -> Dict[str, Any]:
    uri = str(arguments.get("uri", ""))
    should_sanitize = bool(arguments.get("sanitize", True))
    path = _resolve_file_uri(uri)

    if not _is_allowed_path(path):
        raise PermissionError("Path is outside MCP allowed roots.")
    if not os.path.exists(path):
        raise FileNotFoundError("Resource not found.")
    if os.path.isdir(path):
        raise IsADirectoryError("Directory reads are not supported.")

    with open(path, "r", encoding="utf-8", errors="ignore") as file:
        content = file.read()

    if should_sanitize:
        anon = anonymize_text(content)
        content = anon.sanitized_text

    return {
        "content": [{"type": "text", "text": content}],
        "metadata": {"uri": f"file://{path}", "sanitized": should_sanitize},
    }


def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    handlers = {
        "secure_chat": _tool_secure_chat,
        "sanitize_text": _tool_sanitize_text,
        "read_local_resource": _tool_read_local_resource,
    }
    if name not in handlers:
        raise ValueError(f"Unknown tool: {name}")
    return handlers[name](arguments)


def read_resource(uri: str) -> Dict[str, Any]:
    result = _tool_read_local_resource({"uri": uri, "sanitize": True})
    return {
        "contents": [
            {
                "uri": uri,
                "mimeType": "text/plain",
                "text": result["content"][0]["text"],
            }
        ]
    }


def handle_jsonrpc(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
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
            return ok(
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "serverInfo": {"name": MCP_SERVER_NAME, "version": MCP_SERVER_VERSION},
                    "capabilities": get_config()["capabilities"],
                }
            )
        if method == "tools/list":
            return ok({"tools": list_tools()})
        if method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            return ok(call_tool(name=name, arguments=arguments))
        if method == "resources/list":
            return ok({"resources": list_resources()})
        if method == "resources/read":
            uri = params.get("uri", "")
            return ok(read_resource(uri))
        if method == "prompts/list":
            return ok({"prompts": []})
        return error(-32601, f"Method not found: {method}", status=404)
    except PermissionError as exc:
        return error(-32001, str(exc), status=403)
    except FileNotFoundError as exc:
        return error(-32002, str(exc), status=404)
    except Exception as exc:  # pragma: no cover - guardrail path
        return error(-32000, str(exc), status=500)


def json_config_string() -> str:
    return json.dumps(get_config(), indent=2)
