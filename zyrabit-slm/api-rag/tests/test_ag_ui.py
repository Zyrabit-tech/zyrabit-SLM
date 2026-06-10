import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.infrastructure.shared.state_tracker import SovereignStateManager
from app.infrastructure.shared.config import N8N_SERVICE_TOKEN

@pytest.fixture(autouse=True)
def setup_db():
    SovereignStateManager.init_db("/tmp/test_sovereign.db")

@pytest.mark.asyncio
async def test_ag_ui_endpoint_success(client):
    # Mock retriever search
    mock_retriever = client.app.state.retriever_service
    mock_retriever.search = AsyncMock(return_value=[])

    # Mock OllamaStreamAdapter.stream
    async def mock_stream(*args, **kwargs):
        yield "Hello "
        yield "world!"

    with patch("app.infrastructure.inference.ollama_stream_adapter.OllamaStreamAdapter.stream", new=mock_stream), \
         patch("app.domain.use_cases.chat_use_case.ChatUseCase.save_interaction") as mock_save:
        
        payload = {
            "threadId": "test-thread",
            "runId": "test-run",
            "state": {},
            "messages": [
                {
                    "id": "msg-1",
                    "role": "user",
                    "content": "Hello Zyra"
                }
            ],
            "tools": [],
            "context": [],
            "forwardedProps": {}
        }
        
        headers = {"Authorization": f"Bearer {N8N_SERVICE_TOKEN}"}
        response = client.post("/ag-ui/", json=payload, headers=headers)
        assert response.status_code == 200
        
        # Verify the SSE streaming output format
        content = response.text
        lines = [line for line in content.strip().split("\n\n") if line.strip()]
        assert len(lines) >= 6

        events = []
        for line in lines:
            for part in line.split("\n"):
                if part.startswith("data:"):
                    event_data = json.loads(part[5:].strip())
                    events.append(event_data)
        
        types = [e.get("type") for e in events]
        assert any("started" in t.lower() or "run" in t.lower() for t in types)
        assert any("content" in t.lower() for t in types)
        assert any("snapshot" in t.lower() for t in types)

        # Layer isolation check: save_interaction is delegated to ChatUseCase
        mock_save.assert_called_once_with("test-thread", "Hello Zyra", "Hello world!")


@pytest.mark.asyncio
async def test_ag_ui_endpoint_unauthorized(client):
    payload = {
        "threadId": "test-thread",
        "runId": "test-run",
        "state": {},
        "messages": [
            {
                "id": "msg-1",
                "role": "user",
                "content": "Hello Zyra"
            }
        ],
        "tools": [],
        "context": [],
        "forwardedProps": {}
    }
    
    # 1. No auth header
    response = client.post("/ag-ui/", json=payload)
    assert response.status_code == 401
    assert "not authenticated" in response.json()["detail"].lower()

    # 2. Invalid auth header
    headers = {"Authorization": "Bearer bad-token"}
    response = client.post("/ag-ui/", json=payload, headers=headers)
    assert response.status_code == 401
    assert "invalid token" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_ag_ui_endpoint_disconnect(client):
    # Mock retriever search
    mock_retriever = client.app.state.retriever_service
    mock_retriever.search = AsyncMock(return_value=[])

    # Stream adapter yielding many tokens
    async def mock_stream(*args, **kwargs):
        yield "Token 1 "
        yield "Token 2 "
        yield "Token 3 "

    with patch("app.infrastructure.inference.ollama_stream_adapter.OllamaStreamAdapter.stream", new=mock_stream), \
         patch("fastapi.Request.is_disconnected", new_callable=AsyncMock) as mock_disconnected:
        
        # Disconnect on the second token check (First check returns False, second returns True)
        mock_disconnected.side_effect = [False, True]

        payload = {
            "threadId": "test-thread",
            "runId": "test-run",
            "state": {},
            "messages": [
                {
                    "id": "msg-1",
                    "role": "user",
                    "content": "Hello Zyra"
                }
            ],
            "tools": [],
            "context": [],
            "forwardedProps": {}
        }
        
        headers = {"Authorization": f"Bearer {N8N_SERVICE_TOKEN}"}
        response = client.post("/ag-ui/", json=payload, headers=headers)
        assert response.status_code == 200

        # Verify that stream ends prematurely and doesn't yield all tokens or snapshot
        content = response.text
        lines = [line for line in content.strip().split("\n\n") if line.strip()]
        
        events = []
        for line in lines:
            for part in line.split("\n"):
                if part.startswith("data:"):
                    events.append(json.loads(part[5:].strip()))
        
        types = [e.get("type") for e in events]
        
        # Should have RUN_STARTED, TEXT_MESSAGE_START, and only one TEXT_MESSAGE_CONTENT
        assert len(types) <= 3
        assert "run-finished" not in [t.lower() for t in types]
