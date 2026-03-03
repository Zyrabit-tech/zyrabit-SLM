"""Inference adapter for OpenAI-compatible chat completions endpoints."""

from __future__ import annotations

import time
from typing import Any, Dict

import requests

from ..ports.inference_port import (
    InferenceProviderError,
    InferenceProviderPort,
    InferenceRequest,
    InferenceResult,
)


class OpenAICompatibleInferenceAdapter(InferenceProviderPort):
    """HTTP adapter for providers exposing /v1/chat/completions contract."""

    def __init__(
        self,
        endpoint: str,
        api_key: str = "",
        default_timeout_seconds: float = 120.0,
        provider_name: str = "openai_compatible",
    ) -> None:
        self.endpoint = endpoint.strip()
        self.api_key = api_key.strip()
        self.default_timeout_seconds = default_timeout_seconds
        self.provider_name = provider_name

    def generate(self, request: InferenceRequest) -> InferenceResult:
        payload: Dict[str, Any] = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "stream": request.stream,
        }
        if request.options:
            payload.update(request.options)

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        timeout = request.timeout_seconds or self.default_timeout_seconds
        start_time = time.time()
        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=timeout,
            )
        except requests.exceptions.ConnectionError as exc:
            raise InferenceProviderError(
                f"Cannot connect to OpenAI-compatible endpoint ({self.endpoint})."
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise InferenceProviderError(
                f"OpenAI-compatible request timed out after {timeout:.1f}s."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise InferenceProviderError(
                f"OpenAI-compatible request failed: {exc}"
            ) from exc

        latency = max(time.time() - start_time, 0.0)
        if response.status_code != 200:
            raise InferenceProviderError(
                f"OpenAI-compatible server error ({response.status_code}): {response.text}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise InferenceProviderError(
                "OpenAI-compatible endpoint returned invalid JSON response."
            ) from exc

        text = self._extract_text(body)
        return InferenceResult(
            text=text,
            latency_seconds=latency,
            provider=self.provider_name,
            raw_payload=body,
        )

    def health(self) -> Dict[str, Any]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            response = requests.get(
                self.endpoint,
                headers=headers,
                timeout=min(self.default_timeout_seconds, 5.0),
            )
            return {
                "provider": self.provider_name,
                "endpoint": self.endpoint,
                "ok": response.status_code < 500,
                "status_code": response.status_code,
            }
        except requests.exceptions.RequestException:
            return {
                "provider": self.provider_name,
                "endpoint": self.endpoint,
                "ok": False,
                "status_code": None,
            }

    @staticmethod
    def _extract_text(body: Dict[str, Any]) -> str:
        choices = body.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content", "")
                    if isinstance(content, str):
                        return content
        return ""
