"""
OllamaStreamAdapter — Async Streaming Inference for AG-UI.

Unlike the synchronous OllamaInferenceAdapter (which uses requests.post),
this adapter streams tokens one-by-one using httpx.AsyncClient.
Designed exclusively for the AG-UI SSE endpoint.

Architecture Note:
    This adapter lives in the Infrastructure layer (Hexagonal Architecture).
    It implements streaming semantics without altering the existing
    InferenceProviderPort contract — the two adapters coexist.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import httpx

from app.infrastructure.shared.config import SLM_URL
from app.ports.streaming_inference_port import StreamingInferencePort
from app.ports.inference_port import InferenceRequest

logger = logging.getLogger("zyrabit.inference.stream")


class OllamaStreamAdapter(StreamingInferencePort):
    """Async streaming adapter for Ollama /api/generate endpoint."""

    def __init__(
        self,
        endpoint: str | None = None,
        timeout_seconds: float = 300.0,
    ) -> None:
        self.endpoint = (endpoint or f"{SLM_URL}/api/generate").strip()
        self.timeout = httpx.Timeout(timeout_seconds, connect=10.0)

    async def stream_generate(self, request: InferenceRequest) -> AsyncIterator[str]:
        """
        Yield tokens one at a time from Ollama's streaming response.

        Each line from Ollama is a JSON object with a "response" key
        containing the next token fragment. The stream ends when
        "done": true is received.
        """
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "stream": True,
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                self.endpoint,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise RuntimeError(
                        f"Ollama stream error ({response.status_code}): "
                        f"{body.decode(errors='replace')}"
                    )

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning("Skipping non-JSON line from Ollama: %s", line[:80])
                        continue

                    # Ollama signals completion with "done": true
                    if chunk.get("done", False):
                        break

                    token = chunk.get("response", "")
                    if token:
                        yield token

    # Backward compatibility for existing tests
    stream = stream_generate
