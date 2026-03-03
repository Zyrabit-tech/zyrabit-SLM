from fastapi.testclient import TestClient
import tempfile

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


def test_mcp_read_resource_sanitizes_by_default():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, dir="/tmp") as tmp:
        tmp.write("email alice@example.com and ssn 123-45-6789")
        uri = f"file://{tmp.name}"

    payload = {
        "jsonrpc": "2.0",
        "id": "2",
        "method": "resources/read",
        "params": {"uri": uri},
    }
    response = client.post("/mcp", json=payload)
    assert response.status_code == 200
    text = response.json()["result"]["contents"][0]["text"]
    assert "alice@example.com" not in text
    assert "123-45-6789" not in text
    assert "<USER_EMAIL_1>" in text
    assert "<SSN_1>" in text
