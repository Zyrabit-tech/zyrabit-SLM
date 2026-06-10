import os
from app.infrastructure.shared.config import SLM_URL
from app.infrastructure.inference.ollama_inference_adapter import OllamaInferenceAdapter
from app.infrastructure.inference.gemini_inference_adapter import GeminiInferenceAdapter
from app.ports.inference_port import InferenceProviderError

def create_inference_provider():
    """
    Factory to create the inference provider based on environment variables.

    INFERENCE_PROVIDER options:
      - ollama        → Docker container (http://zyrabit-engine:11434)
      - ollama_host   → Native Ollama on Mac Metal (http://host.docker.internal:11434)
      - gemini        → Google Gemini API (requires GEMINI_API_KEY)
    """
    provider_type = os.getenv("INFERENCE_PROVIDER", "ollama").lower()

    if provider_type in ("ollama", "ollama_host"):
        # Both use SLM_URL — the URL itself controls which Ollama instance to hit.
        # ollama_host: SLM_URL=http://host.docker.internal:11434  (native Metal)
        # ollama:      SLM_URL=http://zyrabit-engine:11434         (Docker container)
        return OllamaInferenceAdapter(endpoint=f"{SLM_URL}/api/generate")

    elif provider_type == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        model = os.getenv("MODEL_NAME", "gemini-1.5-flash")
        if not api_key:
            raise InferenceProviderError("GEMINI_API_KEY is required for Gemini provider")
        return GeminiInferenceAdapter(api_key=api_key, model=model)

    else:
        raise InferenceProviderError(
            f"Unknown inference provider: '{provider_type}'. "
            "Valid options: ollama, ollama_host, gemini"
        )
