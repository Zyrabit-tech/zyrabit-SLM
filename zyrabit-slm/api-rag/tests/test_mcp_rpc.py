import pytest
import json
import os
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_mcp_rpc_list_tools():
    """Test listing tools via MCP JSON-RPC."""
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 1
    }
    response = client.post("/mcp/rpc", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert "result" in data
    assert "tools" in data["result"]
    
    # Check for critical tools
    tool_names = [t["name"] for t in data["result"]["tools"]]
    assert "send_telegram_notification" in tool_names

@patch("requests.post")
def test_mcp_rpc_call_telegram_tool_mocked(mock_post):
    """Test calling the Telegram tool via MCP JSON-RPC with mocked network."""
    # Mock successful Telegram response
    mock_post.return_value.status_code = 200
    
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "send_telegram_notification",
            "arguments": {
                "message": "Sovereign Test: Zyrabit Integration Test sequence passed. [Test ID: 999]"
            }
        },
        "id": 100
    }
    response = client.post("/mcp/rpc", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "result" in data
    assert "content" in data["result"]
    result_text = data["result"]["content"][0]["text"]
    assert "Success" in result_text or "Telegram notification sent" in result_text
    
    # Verify the mock was called with PII masking check (if applicable)
    assert mock_post.called
    args, kwargs = mock_post.call_args
    assert "api.telegram.org" in args[0]
    assert "chat_id" in kwargs["json"]

def test_mcp_rpc_call_tool_not_found():
    """Test calling a non-existent tool via MCP JSON-RPC."""
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "non_existent_tool",
            "arguments": {}
        },
        "id": 2
    }
    response = client.post("/mcp/rpc", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert "not found" in data["error"]["message"].lower()

def test_mcp_rpc_invalid_jsonrpc_version():
    """Test sending invalid JSON-RPC version."""
    payload = {
        "jsonrpc": "1.0",
        "method": "tools/list",
        "params": {},
        "id": 3
    }
    response = client.post("/mcp/rpc", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "result" in data or "error" in data
