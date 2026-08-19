"""Port definition for pluggable OpenTelemetry and Prometheus observability."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, ContextManager


class TelemetryPort(ABC):
    """Port for distributed tracing (OpenTelemetry) and metrics recording (Prometheus)."""

    @abstractmethod
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> ContextManager[Any]:
        """Start a distributed tracing span complying with GenAI Semantic Conventions."""

    @abstractmethod
    def record_ttft(self, model: str, device: str, ttft_ms: float) -> None:
        """Record Time-To-First-Token in milliseconds histogram."""

    @abstractmethod
    def record_tokens(self, model: str, prompt_tokens: int, completion_tokens: int) -> None:
        """Record prompt (prefill) and completion (decode) token usage."""

    @abstractmethod
    def record_throughput(self, model: str, device: str, tps: float) -> None:
        """Record generation throughput in tokens per second."""

    @abstractmethod
    def record_rag_search(self, duration_ms: float, hits: int) -> None:
        """Record RAG hybrid search duration and evidence hits count."""

    @abstractmethod
    def record_pii_match(self, entity_type: str, action: str = "masked") -> None:
        """Record detected and masked PII entities."""
