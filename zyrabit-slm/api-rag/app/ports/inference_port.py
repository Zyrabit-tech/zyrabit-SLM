"""Port definitions for pluggable inference providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


class InferenceProviderError(RuntimeError):
    """Raised when an inference provider cannot serve a generation request."""


@dataclass(frozen=True)
class InferenceRequest:
    """Normalized request contract for inference providers."""

    model: str
    prompt: str
    system_prompt: Optional[str] = None
    stream: bool = False
    timeout_seconds: Optional[float] = None
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InferenceResult:
    """Normalized inference result independent from provider-specific payloads."""

    text: str
    latency_seconds: float
    provider: str
    raw_payload: Dict[str, Any] = field(default_factory=dict)


class InferenceProviderPort(ABC):
    """Provider-agnostic inference contract for generate + health operations."""

    @abstractmethod
    def generate(self, request: InferenceRequest) -> InferenceResult:
        """Run inference for a prompt and return normalized output."""

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """Return provider health metadata for diagnostics."""
