from unittest.mock import patch

from app import services
from app.ports.inference_port import InferenceResult


@patch("app.inference_factory.create_inference_provider")
def test_query_secure_slm_never_sends_raw_pii(mock_provider_factory):
    # We no longer mock print because we sanitized logs in the adapter directly
    class DummyProvider:
        def __init__(self) -> None:
            self.last_request = None

        def generate(self, request):
            self.last_request = request
            return InferenceResult(
                text="We will notify <USER_EMAIL_1>.",
                latency_seconds=0.1,
                provider="ollama",
                raw_payload={"response": "We will notify <USER_EMAIL_1>."},
            )

    provider = DummyProvider()
    mock_provider_factory.return_value = provider
    prompt = (
        "My name is Alice Smith, my email is alice@example.com, "
        "phone 415-555-1234 and SSN 123-45-6789"
    )

    response, latency = services.query_secure_slm(prompt)

    assert latency >= 0
    assert "alice@example.com" in response
    sanitized_prompt = provider.last_request.prompt
    assert "alice@example.com" not in sanitized_prompt
    assert "415-555-1234" not in sanitized_prompt
    assert "123-45-6789" not in sanitized_prompt
    assert "<USER_EMAIL_1>" in sanitized_prompt
    assert "<PHONE_1>" in sanitized_prompt
    assert "<SSN_1>" in sanitized_prompt
