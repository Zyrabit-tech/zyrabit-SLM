"""
Factory for creating inference provider adapters dynamically based on configuration.
"""
from app.ports.inference_port import InferenceProviderPort
from app.ports.streaming_inference_port import StreamingInferencePort
from app.infrastructure.inference.ollama_inference_adapter import OllamaInferenceAdapter
from app.infrastructure.inference.ollama_stream_adapter import OllamaStreamAdapter
from app.infrastructure.inference.gemini_inference_adapter import GeminiInferenceAdapter
from app.infrastructure.inference.vllm_inference_adapter import VllmInferenceAdapter
from app.infrastructure.inference.vllm_stream_adapter import VllmStreamAdapter
from app.infrastructure.shared.config import SLM_URL

class InferenceProviderFactory:
    """Factory to instantiate the correct inference adapters based on configuration."""

    @staticmethod
    def create_sync_provider(provider_name: str = "ollama", **kwargs) -> InferenceProviderPort:
        """Creates a synchronous inference provider."""
        if provider_name.lower() == "ollama":
            endpoint = kwargs.get("endpoint", f"{SLM_URL}/api/generate")
            return OllamaInferenceAdapter(endpoint=endpoint)
        elif provider_name.lower() == "vllm":
            endpoint = kwargs.get("endpoint", f"{SLM_URL}/v1/chat/completions")
            return VllmInferenceAdapter(endpoint=endpoint)
        elif provider_name.lower() == "gemini":
            api_key = kwargs.get("api_key")
            if not api_key:
                raise ValueError("API key required for Gemini inference provider.")
            return GeminiInferenceAdapter(api_key=api_key)
        else:
            raise ValueError(f"Unsupported inference provider: {provider_name}")

    @staticmethod
    def create_stream_provider(provider_name: str = "ollama", **kwargs) -> StreamingInferencePort:
        """Creates a streaming inference provider."""
        if provider_name.lower() == "ollama":
            endpoint = kwargs.get("endpoint", f"{SLM_URL}/api/generate")
            return OllamaStreamAdapter(endpoint=endpoint)
        elif provider_name.lower() == "vllm":
            endpoint = kwargs.get("endpoint", f"{SLM_URL}/v1/chat/completions")
            return VllmStreamAdapter(endpoint=endpoint)
        # TODO: Add Gemini stream adapter when needed
        else:
            raise ValueError(f"Unsupported streaming inference provider: {provider_name}")
