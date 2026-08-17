"""Inference adapter for vLLM (OpenAI-compatible) chat completions endpoint."""

from __future__ import annotations

import time
import logging
from typing import Any, Dict
from urllib.parse import urlparse

import requests

logger = logging.getLogger("zyrabit.inference.vllm")

from app.ports.inference_port import (
    InferenceProviderError,
    InferenceProviderPort,
    InferenceRequest,
    InferenceResult,
)


class VllmInferenceAdapter(InferenceProviderPort):
    """HTTP adapter for vLLM /v1/chat/completions endpoint."""

    def __init__(
        self,
        endpoint: str,
        default_timeout_seconds: float = 300.0,
        provider_name: str = "vllm",
    ) -> None:
        self.endpoint = endpoint.strip()
        self.default_timeout_seconds = default_timeout_seconds
        self.provider_name = provider_name

    def generate(self, request: InferenceRequest) -> InferenceResult:
        if request.messages:
            messages = list(request.messages)
        else:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})

        payload: Dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "stream": request.stream,
        }
        
        # Merge options (like temperature, max_tokens)
        if request.options:
            payload.update(request.options)

        timeout = request.timeout_seconds or self.default_timeout_seconds
        start_time = time.time()
        
        try:
            response = requests.post(self.endpoint, json=payload, timeout=timeout)
        except requests.exceptions.ConnectionError as exc:
            raise InferenceProviderError(
                f"Cannot connect to vLLM endpoint ({self.endpoint})."
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise InferenceProviderError(
                f"vLLM request timed out after {timeout:.1f}s."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise InferenceProviderError(f"vLLM request failed: {exc}") from exc

        latency = max(time.time() - start_time, 0.0)
        
        if response.status_code != 200:
            raise InferenceProviderError(
                f"vLLM server error ({response.status_code}): {response.text}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise InferenceProviderError("vLLM returned invalid JSON response.") from exc

        # OpenAI format returns choices array
        choices = body.get("choices", [])
        if not choices:
            text_response = ""
        else:
            text_response = choices[0].get("message", {}).get("content", "")

        return InferenceResult(
            text=text_response,
            latency_seconds=latency,
            provider=self.provider_name,
            raw_payload=body,
        )

    def health(self) -> Dict[str, Any]:
        parsed = urlparse(self.endpoint)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Check basic connectivity using OpenAI models endpoint
        models_url = f"{base_url}/v1/models"
        try:
            response = requests.get(models_url, timeout=5.0)
            if response.status_code != 200:
                return {"provider": self.provider_name, "ok": False, "reason": "Health check failed"}
            
            data = response.json()
            models = [m.get("id") for m in data.get("data", [])]

            return {
                "provider": self.provider_name,
                "endpoint": self.endpoint,
                "ok": True,
                "available_models": models,
                "status": "READY" if models else "WARMING_UP"
            }
        except requests.exceptions.RequestException:
            logger.exception("vLLM health check failed.")
            return {
                "provider": self.provider_name,
                "ok": False,
                "reason": "Cannot connect to vLLM inference provider"
            }
