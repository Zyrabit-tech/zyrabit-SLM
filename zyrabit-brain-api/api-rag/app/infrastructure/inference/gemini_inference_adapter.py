import time
import requests
import logging
from typing import Any, Dict
from ...ports.inference_port import (
    InferenceProviderError,
    InferenceProviderPort,
    InferenceRequest,
    InferenceResult,
)

logger = logging.getLogger("uvicorn.error")

class GeminiInferenceAdapter(InferenceProviderPort):
    """Adapter for Google Gemini API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-1.5-flash-latest",
        default_timeout_seconds: float = 30.0,
        provider_name: str = "gemini",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.default_timeout_seconds = default_timeout_seconds
        self.provider_name = provider_name
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    def generate(self, request: InferenceRequest) -> InferenceResult:
        model = request.model or self.model
        # Re-build endpoint if model changed in request
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": request.prompt}]
            }]
        }

        timeout = request.timeout_seconds or self.default_timeout_seconds
        start_time = time.time()
        
        try:
            response = requests.post(endpoint, json=payload, timeout=timeout)
            response.raise_for_status()
            body = response.json()
        except requests.exceptions.RequestException as exc:
            logger.error(f"Gemini API error: {exc}")
            raise InferenceProviderError(f"Gemini request failed: {exc}") from exc

        latency = time.time() - start_time
        
        # Extract text from Gemini response structure
        try:
            generated_text = body['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError):
            logger.error(f"Invalid Gemini response: {body}")
            raise InferenceProviderError("Gemini returned an unexpected response format.")

        return InferenceResult(
            text=generated_text,
            latency_seconds=latency,
            provider=self.provider_name,
            raw_payload=body,
        )

    def health(self) -> Dict[str, Any]:
        """Simple health check by attempting to list models (verifies API key)."""
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
        try:
            response = requests.get(list_url, timeout=5.0)
            if response.status_code == 200:
                return {"provider": self.provider_name, "ok": True, "status": "CONNECTED"}
            return {"provider": self.provider_name, "ok": False, "reason": f"API returned {response.status_code}"}
        except Exception as e:
            return {"provider": self.provider_name, "ok": False, "reason": str(e)}
