def test_mcp_list_documentation_tools(client):
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 1
    }
    response = client.post("/mcp/rpc", json=payload)
    assert response.status_code == 200
    data = response.json()
    tool_names = [t["name"] for t in data["result"]["tools"]]
    
    assert "get_quick_start_guide" in tool_names
    assert "get_api_reference" in tool_names
    assert "get_docker_compose_example" in tool_names
    assert "get_architecture_overview" in tool_names
    assert "get_troubleshooting_guide" in tool_names
    assert "get_environment_variables_reference" in tool_names
    assert "run_self_diagnostic" in tool_names

def test_mcp_get_quick_start_guide(client):
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "get_quick_start_guide",
            "arguments": {"platform": "windows"}
        },
        "id": 2
    }
    response = client.post("/mcp/rpc", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    text = data["result"]["content"][0]["text"]
    assert "Quickstart Fundamentals" in text

def test_mcp_get_api_reference(client):
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "get_api_reference",
            "arguments": {"endpoint": "chat"}
        },
        "id": 3
    }
    response = client.post("/mcp/rpc", json=payload)
    assert response.status_code == 200
    data = response.json()
    text = data["result"]["content"][0]["text"]
    assert "Chat Completion" in text

def test_mcp_get_troubleshooting_guide(client):
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "get_troubleshooting_guide",
            "arguments": {"error": "oom"}
        },
        "id": 4
    }
    response = client.post("/mcp/rpc", json=payload)
    assert response.status_code == 200
    data = response.json()
    text = data["result"]["content"][0]["text"]
    assert "Debugging Guide" in text

def test_mcp_run_self_diagnostic(client):
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "run_self_diagnostic",
            "arguments": {}
        },
        "id": 5
    }
    response = client.post("/mcp/rpc", json=payload)
    assert response.status_code == 200
    data = response.json()
    text = data["result"]["content"][0]["text"]
    assert "SYSTEM DIAGNOSTIC REPORT" in text
