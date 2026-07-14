"""
Sovereign Circuit Breaker for Inference Providers.

Implements the standard 3-state Circuit Breaker pattern:
  CLOSED   → Normal operation, requests flow through
  OPEN     → Blocking requests after N consecutive failures
  HALF_OPEN → Testing recovery after timeout period

When the circuit opens, it returns an InferenceProviderError with a
human-readable message explaining the situation and suggesting smaller models.

Usage:
    breaker = InferenceCircuitBreaker(failure_threshold=3, recovery_timeout_seconds=30)
    try:
        result = breaker.call(adapter.generate, prompt, model="qwen2.5:7b")
    except InferenceProviderError as e:
        # Circuit is OPEN or exhausted retries
        return {"error": str(e)}
"""
import logging
import time
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("zyrabit.circuit_breaker")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class InferenceCircuitBreaker:
    """
    Circuit breaker protecting inference adapter calls.
    Thread-safe enough for single-worker async FastAPI (asyncio event loop).
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout_seconds: int = 30,
        fallback_model: str = "qwen2.5:1.5b",
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.fallback_model = fallback_model

        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._last_failure_time: Optional[float] = None

    @property
    def state(self) -> CircuitState:
        """Returns the current state, transitioning OPEN → HALF_OPEN if timeout elapsed."""
        if (
            self._state == CircuitState.OPEN
            and self._last_failure_time is not None
            and time.monotonic() - self._last_failure_time >= self.recovery_timeout_seconds
        ):
            logger.warning(
                f"⚡ Circuit HALF_OPEN: Testing inference recovery "
                f"(fallback suggestion: {self.fallback_model})"
            )
            self._state = CircuitState.HALF_OPEN
        return self._state

    def call(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Wraps a callable with circuit breaker logic.
        Raises InferenceProviderError if the circuit is OPEN.
        """
        # Import here to avoid circular imports
        from app.ports.inference_port import InferenceProviderError  # type: ignore[import]

        current_state = self.state

        if current_state == CircuitState.OPEN:
            seconds_until_retry = self.recovery_timeout_seconds - (
                time.monotonic() - (self._last_failure_time or 0)
            )
            raise InferenceProviderError(
                f"🔴 Inference circuit OPEN: Service is recovering. "
                f"Retry in {max(0, int(seconds_until_retry))}s. "
                f"For faster response, consider using a smaller model: {self.fallback_model}"
            )

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Reset circuit on successful call."""
        if self._state != CircuitState.CLOSED:
            logger.info("✅ Circuit CLOSED: Inference provider recovered successfully.")
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None

    def _on_failure(self) -> None:
        """Record failure and potentially open the circuit."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._failure_count >= self.failure_threshold:
            if self._state != CircuitState.OPEN:
                logger.error(
                    f"🔴 Circuit OPEN after {self._failure_count} consecutive failures. "
                    f"Will attempt recovery in {self.recovery_timeout_seconds}s. "
                    f"Suggested fallback: {self.fallback_model}"
                )
            self._state = CircuitState.OPEN
        else:
            logger.warning(
                f"⚠️ Inference failure {self._failure_count}/{self.failure_threshold}. "
                f"Circuit still CLOSED."
            )

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def reset(self) -> None:
        """Manually reset the circuit (useful for testing or admin endpoints)."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        logger.info("🔄 Circuit manually RESET to CLOSED state.")


# Module-level singleton used by the Ollama adapter
_ollama_circuit_breaker: Optional[InferenceCircuitBreaker] = None


def get_ollama_circuit_breaker() -> InferenceCircuitBreaker:
    """Returns the module-level Ollama circuit breaker singleton."""
    global _ollama_circuit_breaker
    if _ollama_circuit_breaker is None:
        _ollama_circuit_breaker = InferenceCircuitBreaker(
            failure_threshold=3,
            recovery_timeout_seconds=30,
            fallback_model="qwen2.5:1.5b",
        )
    return _ollama_circuit_breaker
