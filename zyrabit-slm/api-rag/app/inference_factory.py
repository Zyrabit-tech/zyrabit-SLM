import os
from app.infrastructure.inference.ollama_inference_adapter import OllamaInferenceAdapter
from app.infrastructure.inference.gemini_inference_adapter import GeminiInferenceAdapter
from app.ports.inference_port import InferenceProviderError

def create_inference_provider():
    """
    Factory to create the inference provider based on environment variables.
    Defaults to Ollama if not specified.
    """
    provider_type = os.getenv("INFERENCE_PROVIDER", "ollama").lower()
    
    if provider_type == "ollama":
        slm_url = os.getenv("SLM_URL", "http://zyrabit-engine:11434")
        return OllamaInferenceAdapter(endpoint=f"{slm_url}/api/generate")
        
    elif provider_type == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        model = os.getenv("MODEL_NAME", "gemini-1.5-flash")
        if not api_key:
            raise InferenceProviderError("GEMINI_API_KEY is required for Gemini provider")
        return GeminiInferenceAdapter(api_key=api_key, model=model)
        
    else:
        raise InferenceProviderError(f"Unknown inference provider: {provider_type}")
