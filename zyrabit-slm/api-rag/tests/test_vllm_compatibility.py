import pytest
from unittest.mock import patch, MagicMock
from app.ports.inference_port import InferenceRequest
from app.infrastructure.inference.vllm_inference_adapter import VllmInferenceAdapter
from app.infrastructure.inference.vllm_stream_adapter import VllmStreamAdapter


def test_vllm_generate_standard_payload():
    adapter = VllmInferenceAdapter(endpoint="http://localhost:8090/v1/chat/completions")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "chatcmpl-vllm-test",
        "model": "qwen2.5-7b-instruct",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Sovereign AI output from vLLM."},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 12,
            "completion_tokens": 8,
            "total_tokens": 20,
        },
    }

    with patch("requests.post", return_value=mock_response) as mock_post:
        req = InferenceRequest(
            model="qwen2.5-7b-instruct",
            prompt="What is sovereignty?",
            system_prompt="You are a sovereign AI assistant.",
            options={"temperature": 0.7, "max_tokens": 512},
        )
        result = adapter.generate(req)

        assert mock_post.called
        assert result.text == "Sovereign AI output from vLLM."
        assert result.raw_payload["model"] == "qwen2.5-7b-instruct"
        assert result.raw_payload["usage"]["prompt_tokens"] == 12
        assert result.raw_payload["usage"]["completion_tokens"] == 8


def test_vllm_health_check_online_and_offline():
    adapter = VllmInferenceAdapter(endpoint="http://localhost:8090/v1/chat/completions")

    # When /v1/models succeeds
    mock_res_ok = MagicMock()
    mock_res_ok.status_code = 200
    mock_res_ok.json.return_value = {"data": [{"id": "meta-llama/Llama-3.1-8B-Instruct"}]}

    with patch("requests.get", return_value=mock_res_ok):
        health = adapter.health()
        assert health["ok"] is True
        assert health["model"] == "meta-llama/Llama-3.1-8B-Instruct"

    # When /v1/models fails
    mock_res_err = MagicMock()
    mock_res_err.status_code = 503

    with patch("requests.get", return_value=mock_res_err):
        health = adapter.health()
        assert health["ok"] is False


@pytest.mark.asyncio
async def test_vllm_streaming_sse_chunks():
    stream_adapter = VllmStreamAdapter(endpoint="http://localhost:8090/v1/chat/completions")

    sse_lines = [
        'data: {"choices": [{"delta": {"content": "Sovereignty"}}]}\n',
        'data: {"choices": [{"delta": {"content": " is"}}]}\n',
        'data: {"choices": [{"delta": {"content": " critical."}}]}\n',
        'data: [DONE]\n',
    ]

    async def async_lines():
        for line in sse_lines:
            yield line

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.aiter_lines = async_lines

    class MockStreamContext:
        async def __aenter__(self):
            return mock_resp
        async def __aexit__(self, *args):
            pass

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def get(self, *args, **kwargs):
            res = MagicMock()
            res.status_code = 200
            res.json.return_value = {"data": [{"id": "qwen2.5-7b-instruct"}]}
            return res
        def stream(self, *args, **kwargs):
            return MockStreamContext()

    with patch("httpx.AsyncClient", MockAsyncClient):
        req = InferenceRequest(model="qwen2.5-7b-instruct", prompt="Tell me about sovereignty")
        chunks = []
        async for chunk in stream_adapter.stream_generate(req):
            chunks.append(chunk)

        full_text = "".join(chunks)
        assert full_text == "Sovereignty is critical."
