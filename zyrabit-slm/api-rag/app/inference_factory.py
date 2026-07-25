import os
from app.infrastructure.inference.factory import InferenceProviderFactory

def create_inference_provider():
    """
    Factory to create the inference provider based on environment variables.

    INFERENCE_PROVIDER options:
      - ollama        → Docker container (http://zyrabit-engine:11434)
      - ollama_host   → Native Ollama on Mac Metal (http://host.docker.internal:11434)
      - embedded_metal→ Embedded Llama.cpp directly on Metal GPU
      - mlx           → Apple MLX Framework directly on Metal
      - gemini        → Google Gemini API (requires GEMINI_API_KEY)
    """
    provider_type = os.getenv("INFERENCE_PROVIDER", "ollama").lower()
    api_key = os.getenv("GEMINI_API_KEY")
    return InferenceProviderFactory.create_sync_provider(provider_type, api_key=api_key)

