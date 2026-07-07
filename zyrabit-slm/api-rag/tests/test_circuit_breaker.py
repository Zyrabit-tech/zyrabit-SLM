import pytest
from app.infrastructure.inference.circuit_breaker import InferenceCircuitBreaker, CircuitState
from app.ports.inference_port import InferenceProviderError

def test_circuit_breaker_flow():
    breaker = InferenceCircuitBreaker(
        failure_threshold=3,
        recovery_timeout_seconds=1,
        fallback_model="test-fallback"
    )

    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0

    # Mock callable that fails
    def failing_call():
        raise ValueError("Service down")

    # Call 1: fails
    with pytest.raises(ValueError):
        breaker.call(failing_call)
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 1

    # Call 2: fails
    with pytest.raises(ValueError):
        breaker.call(failing_call)
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 2

    # Call 3: fails -> Circuit Opens
    with pytest.raises(ValueError):
        breaker.call(failing_call)
    assert breaker.state == CircuitState.OPEN
    assert breaker.failure_count == 3

    # Subsequent call while open: raises InferenceProviderError immediately
    with pytest.raises(InferenceProviderError) as exc:
        breaker.call(failing_call)
    assert "recovering" in str(exc.value)

    # Wait for timeout to expire and transition to HALF_OPEN
    import time
    time.sleep(1.1)
    assert breaker.state == CircuitState.HALF_OPEN

    # A successful call under HALF_OPEN closes the circuit
    def successful_call():
        return "success"

    result = breaker.call(successful_call)
    assert result == "success"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0
