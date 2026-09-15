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
        self._cached_model_id: str | None = None

    def get_active_model(self) -> str | None:
        """Dynamically query the active served model from vLLM /v1/models."""
        parsed = urlparse(self.endpoint)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        models_url = f"{base_url}/v1/models"
        try:
            response = requests.get(models_url, timeout=3.0)
            if response.status_code == 200:
                data = response.json()
                models = [m.get("id") for m in data.get("data", []) if m.get("id")]
                if models:
                    self._cached_model_id = models[0]
                    return self._cached_model_id
        except Exception as exc:
            logger.debug("Failed to query active vLLM model: %s", exc)
        return self._cached_model_id

    def generate(self, request: InferenceRequest) -> InferenceResult:
        if request.messages:
            messages = list(request.messages)
        else:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.append({"role": "user", "content": request.prompt})

        # Dynamic model resolution: query the active model loaded in the NPU/GPU engine
        active_model = self.get_active_model()
        target_model = request.model or active_model

        if active_model:
            # If request.model is a tag alias or generic name, prioritize the active served model
            target_model = active_model

        payload: Dict[str, Any] = {
            "model": target_model,
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

        usage = body.get("usage") or {}
        completion_tokens = usage.get("completion_tokens", 0) or 0
        prompt_tokens = usage.get("prompt_tokens", 0) or 0

        existing_zyrabit = body.get("zyrabit") or {}
        tps = existing_zyrabit.get("tps")
        if tps is None and latency > 0 and completion_tokens > 0:
            tps = round(completion_tokens / latency, 2)

        ttft_ms = existing_zyrabit.get("ttft_ms")
        if ttft_ms is None and latency > 0:
            # Estimate TTFT based on prompt processing latency ratio if not provided by stream
            ttft_ms = round(latency * 1000 * 0.2, 2)

        body["zyrabit"] = {
            "ttft_ms": ttft_ms,
            "tps": tps,
            "source": existing_zyrabit.get("engine", self.provider_name),
            "mode": existing_zyrabit.get("mode", "metal"),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_ms": round(latency * 1000, 2),
        }

        is_tt = "8090" in self.endpoint or "tenstorrent" in self.provider_name.lower() or "8000" in self.endpoint
        device = "tenstorrent_tensix" if is_tt else ("nvidia_cuda" if "cuda" in self.provider_name.lower() else "apple_metal")
        execution_target = {
            "engine": "vllm",
            "device": device,
            "backend": "vllm_tt_metal" if is_tt else "vllm_native",
            "accelerated": True,
        }

        return InferenceResult(
            text=text_response,
            latency_seconds=latency,
            provider=self.provider_name,
            raw_payload=body,
            execution_target=execution_target,
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
                "model": models[0] if models else None,
                "status": "READY" if models else "WARMING_UP"
            }
        except requests.exceptions.RequestException:
            logger.exception("vLLM health check failed.")
            return {
                "provider": self.provider_name,
                "ok": False,
                "reason": "Cannot connect to vLLM inference provider"
            }
