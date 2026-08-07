"""Inference adapter for native Apple Silicon MLX models."""

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

# MLX initialises native Metal components. Keep that side effect behind the
# selected provider so imports, Ollama deployments and CPU CI remain portable.
mx = None
load = None
generate = None


def _load_mlx_runtime() -> bool:
    global mx, load, generate
    if load is not None and generate is not None:
        return True
    try:
        import mlx.core as mlx_core
        from mlx_lm import generate as mlx_generate, load as mlx_load
        mx, load, generate = mlx_core, mlx_load, mlx_generate
        return True
    except ImportError:
        logger.warning("mlx-lm or mlx not installed. MLX inference will not be available.")
        return False


class MlxInferenceAdapter(InferenceProviderPort):
    """Adapter executing inference via Apple Silicon native MLX engine."""

    def __init__(self, provider_name: str = "mlx") -> None:
        self.provider_name = provider_name
        self.downloader = ModelDownloader()
        self._loaded_models: Dict[str, tuple[Any, Any]] = {} # (model, tokenizer)

    def _get_or_load_model(self, model_name: str) -> tuple[Any, Any]:
        if load is None and not _load_mlx_runtime():
            raise InferenceProviderError("mlx-lm/mlx is not installed on this system.")

        if model_name in self._loaded_models:
            return self._loaded_models[model_name]

        model_path = self.downloader.get_model_path(model_name, "mlx")
        logger.info(f"Loading MLX model into Unified Memory (Metal GPU): {model_path}")
        
        try:
            model, tokenizer = load(model_path)
            self._loaded_models[model_name] = (model, tokenizer)
            return model, tokenizer
        except Exception as exc:
            logger.error(f"Failed to initialize MLX model: {exc}")
            raise InferenceProviderError(f"MLX model initialization failed: {exc}") from exc

    def generate(self, request: InferenceRequest) -> InferenceResult:
        model, tokenizer = self._get_or_load_model(request.model)

        prompt = request.prompt
        if request.system_prompt:
            prompt = f"<|im_start|>system\n{request.system_prompt}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"

        start_time = time.time()
        try:
            # Execute mlx-lm generation
            text = generate(
                model,
                tokenizer,
                prompt=prompt,
                max_tokens=request.options.get("max_tokens", 512),
                temp=request.options.get("temperature", 0.7),
            )
            latency = max(time.time() - start_time, 0.0)

            # Strip chat structure tags if they leak into text
            text = text.replace("<|im_end|>", "").strip()

            # Estimate token count (simple word split fallback or length evaluation)
            token_count = len(text.split())

            raw_payload = {
                "model": request.model,
                "response": text,
                "done": True,
                "eval_count": token_count,
                "eval_duration": latency * 1e9,
            }

            return InferenceResult(
                text=text,
                latency_seconds=latency,
                provider=self.provider_name,
                raw_payload=raw_payload,
            )

        except Exception as exc:
            logger.error(f"MLX generation failed: {exc}")
            raise InferenceProviderError(f"MLX generation failed: {exc}") from exc

    def health(self) -> Dict[str, Any]:
        if mx is None and not _load_mlx_runtime():
            return {
                "provider": self.provider_name,
                "ok": False,
                "reason": "mlx/mlx-lm not installed"
            }
        return {
            "provider": self.provider_name,
            "ok": True,
            "loaded_models": list(self._loaded_models.keys()),
            "status": "READY"
        }
