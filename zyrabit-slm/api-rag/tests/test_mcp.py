import tempfile

def test_mcp_config_endpoint(client):
    response = client.get("/mcp/config.json")
    assert response.status_code == 200
    data = response.json()
    assert "capabilities" in data
    assert "tools" in data["capabilities"]

def test_mcp_tools_list(client):
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tools/list",
        "params": {}
    }
    response = client.post("/mcp/rpc", json=payload)
    assert response.status_code == 200
    tools = response.json()["result"]["tools"]
    names = {tool["name"] for tool in tools}
    assert "secure_query" in names
    assert "send_telegram_notification" in names



