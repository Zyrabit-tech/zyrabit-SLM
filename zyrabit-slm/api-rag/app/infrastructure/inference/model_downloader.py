"""Utility for downloading foundation models from HuggingFace Hub to local cache."""

from __future__ import annotations

import os
import logging
from pathlib import Path

logger = logging.getLogger("zyrabit.inference")

try:
    from huggingface_hub import hf_hub_download, snapshot_download
except ImportError:
    logger.warning("huggingface_hub not installed. Model downloading will not be available.")

# Model registry maps logical model name to HF repository details
MODEL_REGISTRY = {
    "qwen2.5:1.5b": {
        "gguf": {
            "repo_id": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
            "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        },
        "mlx": {
            "repo_id": "mlx-community/Qwen2.5-1.5B-Instruct-4bit",
        }
    },
    "qwen2.5:7b": {
        "gguf": {
            "repo_id": "Qwen/Qwen2.5-7B-Instruct-GGUF",
            "filename": "qwen2.5-7b-instruct-q4_k_m.gguf",
        },
        "mlx": {
            "repo_id": "mlx-community/Qwen2.5-7B-Instruct-4bit",
        }
    }
}

DEFAULT_CACHE_DIR = Path(os.path.expanduser("~/.cache/zyrabit/models"))


class ModelDownloader:
    """Orchestrates model download from HuggingFace to a local cache directory."""

    def __init__(self, cache_dir: Path = DEFAULT_CACHE_DIR) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_model_path(self, model_name: str, format_type: str = "gguf") -> str:
        """Returns local path to the model, downloading if not present."""
        normalized_name = model_name.lower().strip()
        
        # If it's already an absolute or relative path to an existing file/dir, return it directly
        if os.path.exists(normalized_name):
            return normalized_name

        if normalized_name not in MODEL_REGISTRY:
            # Fallback default maps to qwen2.5:1.5b
            normalized_name = "qwen2.5:1.5b"
            
        config = MODEL_REGISTRY[normalized_name].get(format_type)
        if not config:
            raise ValueError(f"No configuration found for model '{model_name}' and format '{format_type}'")

        repo_id = config["repo_id"]

        if format_type == "gguf":
            filename = config["filename"]
            local_path = self.cache_dir / filename
            if local_path.exists():
                logger.info(f"Using cached GGUF model: {local_path}")
                return str(local_path)

            # Search in alternative local paths before downloading
            search_dirs = [
                Path("zyrabit-slm/models"),
                Path.home() / "models",
                Path.home() / ".cache" / "lm-studio" / "models",
                Path.home() / ".ollama" / "models",
            ]
            for search_dir in search_dirs:
                if search_dir.exists():
                    for match in search_dir.rglob(f"*{filename}*"):
                        if match.is_file() and match.stat().st_size > 100_000_000:
                            logger.info(f"Auto-detected existing GGUF model at: {match}")
                            return str(match)

            logger.info(f"Downloading GGUF model '{filename}' from repo '{repo_id}' to cache...")
            try:
                downloaded_file = hf_hub_download(
                    repo_id=repo_id,
                    filename=filename,
                    local_dir=self.cache_dir,
                    local_dir_use_symlinks=False,
                )
                return str(downloaded_file)
            except Exception as exc:
                logger.error(f"Failed to download GGUF model {model_name} from HuggingFace: {exc}")
                raise RuntimeError(f"Failed to download GGUF model: {exc}") from exc

        elif format_type == "mlx":
            local_path = self.cache_dir / repo_id.split("/")[-1]
            if local_path.exists() and any(local_path.iterdir()):
                logger.info(f"Using cached MLX model directory: {local_path}")
                return str(local_path)

            logger.info(f"Downloading MLX model snapshot from repo '{repo_id}' to cache...")
            try:
                downloaded_dir = snapshot_download(
                    repo_id=repo_id,
                    local_dir=local_path,
                    local_dir_use_symlinks=False,
                )
                return str(downloaded_dir)
            except Exception as exc:
                logger.error(f"Failed to download MLX model {model_name} from HuggingFace: {exc}")
                raise RuntimeError(f"Failed to download MLX model: {exc}") from exc
                
        else:
            raise ValueError(f"Unsupported format type: {format_type}")
