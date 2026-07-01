"""Port definition for streaming inference providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator
from .inference_port import InferenceRequest

class StreamingInferencePort(ABC):
    """Provider-agnostic streaming inference contract."""

    @abstractmethod
    async def stream_generate(self, request: InferenceRequest) -> AsyncIterator[str]:
        """Run inference for a prompt and yield stream chunks."""
