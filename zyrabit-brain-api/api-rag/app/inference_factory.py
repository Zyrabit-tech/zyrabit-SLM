"""Factory for pluggable inference provider adapters."""

from __future__ import annotations

import os

from .adapters.ollama_inference_adapter import OllamaInferenceAdapter
from .adapters.openai_compatible_inference_adapter import (
    OpenAICompatibleInferenceAdapter,
)
from .ports.inference_port import InferenceProviderError, InferenceProviderPort


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
            endpoint=os.getenv("SLM_URL", "http://slm-engine:11434/api/generate"),
            default_timeout_seconds=timeout_seconds,
            provider_name=provider,
        )

    if provider in {"openai", "openai_compatible", "openai-compatible"}:
        return OpenAICompatibleInferenceAdapter(
            endpoint=os.getenv(
                "INFERENCE_BASE_URL",
                "http://localhost:8000/v1/chat/completions",
            ),
            api_key=os.getenv("INFERENCE_API_KEY", ""),
            default_timeout_seconds=timeout_seconds,
            provider_name="openai_compatible",
        )

    raise InferenceProviderError(
        "Unsupported INFERENCE_PROVIDER "
        f"'{provider}'. Supported values: ollama, ollama_host, "
        "ollama_docker, openai_compatible."
    )
