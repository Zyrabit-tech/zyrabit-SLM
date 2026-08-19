"""vLLM Stream Adapter — Async Streaming Inference for AG-UI."""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import httpx

from app.ports.streaming_inference_port import StreamingInferencePort
from app.ports.inference_port import InferenceRequest

logger = logging.getLogger("zyrabit.inference.stream.vllm")


class VllmStreamAdapter(StreamingInferencePort):
    """Async streaming adapter for vLLM /v1/chat/completions endpoint."""

    def __init__(
        self,
        endpoint: str,
        timeout_seconds: float = 300.0,
    ) -> None:
        self.endpoint = endpoint.strip()
        self.timeout = httpx.Timeout(timeout_seconds, connect=10.0)
        self._cached_model_id: str | None = None

    async def get_active_model(self, client: httpx.AsyncClient) -> str | None:
        """Dynamically query active served model from vLLM."""
        from urllib.parse import urlparse
        parsed = urlparse(self.endpoint)
        models_url = f"{parsed.scheme}://{parsed.netloc}/v1/models"
        try:
            res = await client.get(models_url, timeout=3.0)
            if res.status_code == 200:
                data = res.json()
                models = [m.get("id") for m in data.get("data", []) if m.get("id")]
                if models:
                    self._cached_model_id = models[0]
                    return self._cached_model_id
        except Exception:
            pass
        return self._cached_model_id

    async def stream_generate(self, request: InferenceRequest) -> AsyncIterator[str]:
        """
        Yield tokens one at a time from vLLM's streaming response.

        vLLM uses SSE (Server-Sent Events) formatted as `data: {...}`
        where `choices[0].delta.content` contains the token fragment.
        """
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            active_model = await self.get_active_model(client)
            target_model = active_model or request.model
            payload = {
                "model": target_model,
                "messages": messages,
                "stream": True,
            }
        
        if request.options:
            payload.update(request.options)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                self.endpoint,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise RuntimeError(
                        f"vLLM stream error ({response.status_code}): "
                        f"{body.decode(errors='replace')}"
                    )

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                        
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            logger.warning("Skipping non-JSON line from vLLM: %s", line[:80])
                            continue

                        choices = chunk.get("choices", [])
                        if not choices:
                            continue
                            
                        delta = choices[0].get("delta", {})
                        token = delta.get("content", "")
                        
                        if token:
                            yield token
