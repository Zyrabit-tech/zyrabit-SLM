"""Factory for pluggable inference provider adapters."""

from __future__ import annotations

import os

from app.infrastructure.inference.ollama_inference_adapter import OllamaInferenceAdapter
from app.infrastructure.inference.gemini_inference_adapter import GeminiInferenceAdapter
from app.ports.inference_port import InferenceProviderError, InferenceProviderPort


def _read_timeout_seconds() -> float:
    raw_value = os.getenv("INFERENCE_TIMEOUT_SECONDS", "120").strip()
    try:
        timeout = float(raw_value)
        if timeout <= 0:
            raise ValueError
        return timeout
    except ValueError:
        return 120.0


def create_inference_provider() -> InferenceProviderPort:
    """Build an inference adapter from environment configuration."""
    provider = os.getenv("INFERENCE_PROVIDER", "ollama").strip().lower()
    timeout_seconds = _read_timeout_seconds()

    if provider in {"ollama", "ollama_host", "ollama_docker"}:
        return OllamaInferenceAdapter(
            endpoint=os.getenv("SLM_URL", "http://zyrabit-engine:11434/api/generate"),
            default_timeout_seconds=timeout_seconds,
            provider_name=provider,
        )

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise InferenceProviderError("GEMINI_API_KEY is required for Gemini provider.")
        
        return GeminiInferenceAdapter(
            api_key=api_key,
            model=os.getenv("MODEL_NAME", "gemini-1.5-flash-latest"),
            default_timeout_seconds=timeout_seconds
        )

    raise InferenceProviderError(
        "Unsupported INFERENCE_PROVIDER "
        f"'{provider}'. Supported values: ollama, gemini."
    )
