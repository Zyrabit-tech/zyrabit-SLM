from unittest.mock import MagicMock, patch
import pytest

from app.ports.inference_port import InferenceRequest
from app.infrastructure.inference.factory import InferenceProviderFactory
from app.infrastructure.inference.llama_cpp_embedded_adapter import LlamaCppEmbeddedAdapter
from app.infrastructure.inference.mlx_inference_adapter import MlxInferenceAdapter
from app.domain.services.whisper_transcription_service import WhisperTranscriptionService


def test_factory_creates_embedded_metal_provider():
    provider = InferenceProviderFactory.create_sync_provider("embedded_metal")
    assert isinstance(provider, LlamaCppEmbeddedAdapter)


def test_factory_creates_mlx_provider():
    provider = InferenceProviderFactory.create_sync_provider("mlx")
    assert isinstance(provider, MlxInferenceAdapter)


@patch("app.infrastructure.inference.llama_cpp_embedded_adapter.Llama")
@patch.object(LlamaCppEmbeddedAdapter, "__init__", lambda self: None)
def test_llama_cpp_adapter_generate(mock_llama_class):
    mock_instance = MagicMock()
    mock_instance.return_value = {
        "choices": [{"text": "Hello from GGUF Metal"}],
        "usage": {"completion_tokens": 10, "prompt_tokens": 5}
    }
    mock_llama_class.return_value = mock_instance

    adapter = LlamaCppEmbeddedAdapter()
    adapter.provider_name = "embedded_metal"
    adapter.downloader = MagicMock()
    adapter.downloader.get_model_path.return_value = "/fake/path/model.gguf"
    adapter._loaded_models = {}

    req = InferenceRequest(model="qwen2.5:1.5b", prompt="Hi")
    res = adapter.generate(req)

    assert res.text == "Hello from GGUF Metal"
    assert res.provider == "embedded_metal"


@patch("app.infrastructure.inference.mlx_inference_adapter.generate")
@patch("app.infrastructure.inference.mlx_inference_adapter.load")
@patch.object(MlxInferenceAdapter, "__init__", lambda self: None)
def test_mlx_adapter_generate(mock_load, mock_generate):
    mock_model = MagicMock()
    mock_tokenizer = MagicMock()
    mock_load.return_value = (mock_model, mock_tokenizer)
    mock_generate.return_value = "Hello from MLX Apple Silicon"

    adapter = MlxInferenceAdapter()
    adapter.provider_name = "mlx"
    adapter.downloader = MagicMock()
    adapter.downloader.get_model_path.return_value = "/fake/path/mlx_model"
    adapter._loaded_models = {}

    req = InferenceRequest(model="qwen2.5:1.5b", prompt="Hi")
    res = adapter.generate(req)

    assert res.text == "Hello from MLX Apple Silicon"
    assert res.provider == "mlx"


@patch("app.domain.services.whisper_transcription_service.WhisperModel")
def test_whisper_transcription_service(mock_whisper_class):
    mock_model = MagicMock()
    mock_segment = MagicMock()
    mock_segment.start = 0.0
    mock_segment.end = 2.5
    mock_segment.text = " Hello world transcription"
    mock_segment.avg_logprob = -0.15

    mock_info = MagicMock()
    mock_info.language = "en"
    mock_info.language_probability = 0.98
    mock_info.duration = 2.5

    mock_model.transcribe.return_value = ([mock_segment], mock_info)
    mock_whisper_class.return_value = mock_model

    service = WhisperTranscriptionService(model_name="base", device="cpu")
    res = service.transcribe("/path/to/test.mp3")

    assert res["text"] == "Hello world transcription"
    assert res["language"] == "en"
    mock_model.transcribe.assert_called_once_with(
        "/path/to/test.mp3",
        beam_size=5,
        language=None,
        vad_filter=True
    )
