"""Inference adapter for Ollama-compatible /api/generate endpoint."""

from __future__ import annotations

import time
from typing import Any, Dict
from urllib.parse import urlparse

import requests

from app.ports.inference_port import (
    InferenceProviderError,
    InferenceProviderPort,
    InferenceRequest,
    InferenceResult,
)


class OllamaInferenceAdapter(InferenceProviderPort):
    """HTTP adapter for Ollama generation endpoint."""

    def __init__(
        self,
        endpoint: str,
        default_timeout_seconds: float = 300.0,
        provider_name: str = "ollama",
    ) -> None:
        self.endpoint = endpoint.strip()
        self.default_timeout_seconds = default_timeout_seconds
        self.provider_name = provider_name

    def generate(self, request: InferenceRequest) -> InferenceResult:
        payload: Dict[str, Any] = {
            "model": request.model,
            "prompt": request.prompt,
            "stream": request.stream,
        }
        if request.options:
            payload.update(request.options)

        timeout = request.timeout_seconds or self.default_timeout_seconds
        start_time = time.time()
        try:
            response = requests.post(self.endpoint, json=payload, timeout=timeout)
        except requests.exceptions.ConnectionError as exc:
            raise InferenceProviderError(
                f"Cannot connect to Ollama endpoint ({self.endpoint})."
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise InferenceProviderError(
                f"Ollama request timed out after {timeout:.1f}s."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise InferenceProviderError(f"Ollama request failed: {exc}") from exc

        latency = max(time.time() - start_time, 0.0)
        if response.status_code != 200:
            raise InferenceProviderError(
                f"Ollama server error ({response.status_code}): {response.text}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise InferenceProviderError("Ollama returned invalid JSON response.") from exc

        return InferenceResult(
            text=str(body.get("response", "")),
            latency_seconds=latency,
            provider=self.provider_name,
            raw_payload=body,
        )

    def health(self) -> Dict[str, Any]:
        parsed = urlparse(self.endpoint)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # 1. Check basic connectivity
        tags_url = f"{base_url}/api/tags"
        try:
            response = requests.get(tags_url, timeout=5.0)
            if response.status_code != 200:
                return {"provider": self.provider_name, "ok": False, "reason": "Health check failed"}
            
            tags_data = response.json()
            models = [m.get("name") for m in tags_data.get("models", [])]
            
            # 2. Check if any model is currently loaded (in RAM) via /api/ps
            ps_url = f"{base_url}/api/ps"
            is_loaded = False
            try:
                ps_res = requests.get(ps_url, timeout=2.0)
                if ps_res.status_code == 200:
                    ps_data = ps_res.json()
                    is_loaded = len(ps_data.get("models", [])) > 0
            except Exception:
                pass # ps might not be available in older Ollama versions

            return {
                "provider": self.provider_name,
                "endpoint": self.endpoint,
                "ok": True,
                "available_models": models,
                "model_loaded": is_loaded,
                "status": "READY" if is_loaded else "WARMING_UP"
            }
        except requests.exceptions.RequestException:
            logger.exception("Ollama health check failed.")
            return {
                "provider": self.provider_name,
                "ok": False,
                "reason": "Cannot connect to inference provider"
            }
