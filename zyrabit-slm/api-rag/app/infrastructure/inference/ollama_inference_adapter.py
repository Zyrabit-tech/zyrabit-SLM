"""Inference adapter for Ollama-compatible /api/generate endpoint."""

from __future__ import annotations

import time
import logging
from typing import Any, Dict
from urllib.parse import urlparse

import requests

logger = logging.getLogger("zyrabit.inference")

from app.ports.inference_port import (
    InferenceProviderError,
    InferenceProviderPort,
    InferenceRequest,
    InferenceResult,
)
from app.infrastructure.inference.circuit_breaker import get_ollama_circuit_breaker

# Exponential backoff delays between retries (seconds)
_RETRY_DELAYS = [1, 2, 4]


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
        breaker = get_ollama_circuit_breaker()
        return breaker.call(self._generate_with_retry, request)

    def _generate_with_retry(self, request: InferenceRequest) -> InferenceResult:
        """Internal generate with exponential backoff retry (3 attempts)."""
        is_chat = bool(request.messages)
        target_url = self.endpoint.replace("/api/generate", "/api/chat") if is_chat else self.endpoint
        payload: Dict[str, Any] = {
            "model": request.model,
            "stream": request.stream,
            "options": {"num_ctx": 4096},
        }
        if is_chat:
            payload["messages"] = list(request.messages)
        else:
            payload["prompt"] = request.prompt
            if request.system_prompt:
                payload["system"] = request.system_prompt

        if request.options:
            for key, value in request.options.items():
                if key in ("format",):
                    payload[key] = value
                else:
                    payload["options"][key] = value

        timeout = request.timeout_seconds or self.default_timeout_seconds
        last_exc: Exception = InferenceProviderError("No attempts made")

        for attempt, delay in enumerate(_RETRY_DELAYS):
            start_time = time.time()
            try:
                response = requests.post(target_url, json=payload, timeout=timeout)
                latency = max(time.time() - start_time, 0.0)

                if response.status_code != 200:
                    raise InferenceProviderError(
                        f"Ollama server error ({response.status_code}): {response.text}"
                    )

                try:
                    body = response.json()
                except ValueError as exc:
                    raise InferenceProviderError("Ollama returned invalid JSON response.") from exc

                if is_chat:
                    response_text = str(body.get("message", {}).get("content", ""))
                else:
                    response_text = str(body.get("response", ""))

                import re
                if "<think>" in response_text and "</think>" in response_text:
                    response_text = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL).strip()

                prompt_eval_dur = body.get("prompt_eval_duration", 0) or 0
                eval_dur = body.get("eval_duration", 0) or 0
                eval_count = body.get("eval_count", 0) or 0
                prompt_eval_count = body.get("prompt_eval_count", 0) or 0

                ttft_ms = round(prompt_eval_dur / 1_000_000, 2) if prompt_eval_dur > 0 else None
                tps = round(eval_count / (eval_dur / 1_000_000_000), 2) if eval_dur > 0 and eval_count > 0 else None

                body["zyrabit"] = {
                    "ttft_ms": ttft_ms,
                    "tps": tps,
                    "source": "ollama",
                    "mode": "metal" if "host" in self.endpoint else "docker",
                    "prompt_tokens": prompt_eval_count,
                    "completion_tokens": eval_count,
                    "total_ms": round(latency * 1000, 2),
                }

                execution_target = {
                    "engine": "ollama",
                    "device": "cpu_generic",
                    "backend": "ollama_host" if "host" in self.endpoint else "ollama_docker",
                    "accelerated": False,
                }

                return InferenceResult(
                    text=response_text,
                    latency_seconds=latency,
                    provider=self.provider_name,
                    raw_payload=body,
                    execution_target=execution_target,
                )

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                last_exc = InferenceProviderError(f"Ollama connection error (attempt {attempt + 1}): {exc}")
                if attempt < len(_RETRY_DELAYS) - 1:
                    logger.warning(f"⚠️ Inference retry {attempt + 1}/{len(_RETRY_DELAYS)} in {delay}s...")
                    time.sleep(delay)
            except InferenceProviderError:
                raise  # Don't retry on logical errors (bad JSON, bad status)
            except requests.exceptions.RequestException as exc:
                raise InferenceProviderError(f"Ollama request failed: {exc}") from exc

        raise last_exc

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
        except requests.exceptions.RequestException as e:
            logger.warning(f"Ollama health check unreachable: {e}")
            return {
                "provider": self.provider_name,
                "ok": False,
                "reason": "Cannot connect to inference provider"
            }
