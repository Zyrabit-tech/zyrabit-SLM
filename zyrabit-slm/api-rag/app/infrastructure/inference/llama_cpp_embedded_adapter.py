"""Inference adapter for embedded llama.cpp runtime (no external server required)."""

from __future__ import annotations

import time
import logging
from typing import Any, Dict

from app.ports.inference_port import (
    InferenceProviderError,
    InferenceProviderPort,
    InferenceRequest,
    InferenceResult,
)
from app.infrastructure.inference.model_downloader import ModelDownloader

logger = logging.getLogger("zyrabit.inference")

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None
    logger.warning("llama-cpp-python not installed. Embedded inference will not be available.")


class LlamaCppEmbeddedAdapter(InferenceProviderPort):
    """Adapter executing inference natively within the Python process via llama.cpp."""

    def __init__(self, provider_name: str = "embedded_metal") -> None:
        self.provider_name = provider_name
        self.downloader = ModelDownloader()
        self._loaded_models: Dict[str, Llama] = {}

    def _get_or_load_model(self, model_name: str) -> Llama:
        if Llama is None:
            raise InferenceProviderError("llama-cpp-python is not installed on this system.")

        if model_name in self._loaded_models:
            return self._loaded_models[model_name]

        model_path = self.downloader.get_model_path(model_name, "gguf")
        logger.info(f"Loading GGUF model into Apple Silicon Metal GPU memory: {model_path}")
        
        try:
            # Load with GPU acceleration enabled by default
            # n_gpu_layers=-1 delegates all model layers to Apple Metal GPU
            llm = Llama(
                model_path=model_path,
                n_gpu_layers=-1,
                n_ctx=4096,
                verbose=False
            )
            self._loaded_models[model_name] = llm
            return llm
        except Exception as exc:
            logger.error(f"Failed to initialize embedded llama.cpp model: {exc}")
            raise InferenceProviderError(f"Embedded model initialization failed: {exc}") from exc

    def generate(self, request: InferenceRequest) -> InferenceResult:
        llm = self._get_or_load_model(request.model)

        prompt = request.prompt
        if request.system_prompt:
            prompt = f"<|im_start|>system\n{request.system_prompt}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"

        start_time = time.time()
        try:
            # Invoke the model directly
            # Suppress excessive print statements from low-level C code
            response = llm(
                prompt,
                max_tokens=request.options.get("max_tokens", 512),
                temperature=request.options.get("temperature", 0.7),
                top_p=request.options.get("top_p", 0.9),
                stop=["<|im_end|>", "<|im_start|>", "\n\nUser:", "User:"],
            )
            latency = max(time.time() - start_time, 0.0)

            choice = response["choices"][0]
            text = choice["text"].strip()

            # Construct simulated Ollama metadata for seamless upstream parsing
            raw_payload = {
                "model": request.model,
                "response": text,
                "done": True,
                "eval_count": response["usage"]["completion_tokens"],
                "prompt_eval_count": response["usage"]["prompt_tokens"],
                "eval_duration": latency * 1e9,
            }

            return InferenceResult(
                text=text,
                latency_seconds=latency,
                provider=self.provider_name,
                raw_payload=raw_payload,
            )

        except Exception as exc:
            logger.error(f"Embedded inference generation failed: {exc}")
            raise InferenceProviderError(f"Embedded generation failed: {exc}") from exc

    def health(self) -> Dict[str, Any]:
        if Llama is None:
            return {
                "provider": self.provider_name,
                "ok": False,
                "reason": "llama-cpp-python not installed"
            }
        return {
            "provider": self.provider_name,
            "ok": True,
            "loaded_models": list(self._loaded_models.keys()),
            "status": "READY"
        }
