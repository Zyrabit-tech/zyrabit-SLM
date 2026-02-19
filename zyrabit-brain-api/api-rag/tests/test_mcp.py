from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_mcp_config_endpoint():
    response = client.get("/mcp/config.json")
    assert response.status_code == 200
    data = response.json()
    assert data["transport"]["endpoint"] == "/mcp"
    assert "tools" in data["capabilities"]


def test_mcp_tools_list():
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tools/list",
        "params": {}
    }
    response = client.post("/mcp", json=payload)
    assert response.status_code == 200
    tools = response.json()["result"]["tools"]
    names = {tool["name"] for tool in tools}
    assert "secure_chat" in names
    assert "sanitize_text" in names
