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
from app.infrastructure.inference.llama_cpp_embedded_adapter import LlamaCppEmbeddedAdapter
from app.infrastructure.inference.mlx_inference_adapter import MlxInferenceAdapter
from app.infrastructure.shared.config import SLM_URL

class InferenceProviderFactory:
    """Factory to instantiate the correct inference adapters based on configuration."""

    @staticmethod
    def create_sync_provider(provider_name: str = "ollama", **kwargs) -> InferenceProviderPort:
        """Creates a synchronous inference provider."""
        provider_lower = provider_name.lower()
        if provider_lower in ("ollama", "ollama_host", "ollama_docker"):
            endpoint = kwargs.get("endpoint", f"{SLM_URL}/api/generate")
            return OllamaInferenceAdapter(endpoint=endpoint)
        elif provider_lower == "embedded_metal":
            return LlamaCppEmbeddedAdapter()
        elif provider_lower == "mlx":
            return MlxInferenceAdapter()
        elif provider_lower == "vllm":
            endpoint = kwargs.get("endpoint", f"{SLM_URL}/v1/chat/completions")
            return VllmInferenceAdapter(endpoint=endpoint)
        elif provider_lower == "gemini":
            api_key = kwargs.get("api_key")
            model_name = kwargs.get("model_name")
            if not api_key:
                raise ValueError("API key required for Gemini inference provider.")
            adapter_kwargs = {"api_key": api_key}
            if model_name:
                adapter_kwargs["model"] = model_name
            return GeminiInferenceAdapter(**adapter_kwargs)
        else:
            from app.ports.inference_port import InferenceProviderError
            raise InferenceProviderError(f"Unsupported inference provider: {provider_name}")

    @staticmethod
    def create_stream_provider(provider_name: str = "ollama", **kwargs) -> StreamingInferencePort:
        """Creates a streaming inference provider."""
        provider_lower = provider_name.lower()
        if provider_lower in ("ollama", "ollama_host", "ollama_docker"):
            endpoint = kwargs.get("endpoint", f"{SLM_URL}/api/generate")
            return OllamaStreamAdapter(endpoint=endpoint)
        elif provider_lower == "vllm":
            endpoint = kwargs.get("endpoint", f"{SLM_URL}/v1/chat/completions")
            return VllmStreamAdapter(endpoint=endpoint)
        # TODO: Add Gemini stream adapter when needed
        else:
            raise ValueError(f"Unsupported streaming inference provider: {provider_name}")
