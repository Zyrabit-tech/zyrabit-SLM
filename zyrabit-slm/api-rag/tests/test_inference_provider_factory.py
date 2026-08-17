# ==============================================================================
# JUSTIFICACIÓN DE MOCKS EN PRUEBAS (PROVIDER FACTORY ISOLATION)
# ==============================================================================
# Propósito: Validar que la fábrica de inferencia construye e instancia los adaptadores
# correctos (Ollama, vLLM, Tenstorrent, Gemini) según las variables de entorno.
# Justificación:
# Se utiliza `unittest.mock.patch` sobre el entorno y llamadas HTTP de sondeo para
# verificar la lógica de selección de adaptadores sin necesidad de conexión física
# a endpoints remotos durante la ejecución de los tests.
# ==============================================================================

from unittest.mock import MagicMock, patch

import pytest
import requests

from app.infrastructure.inference.ollama_inference_adapter import OllamaInferenceAdapter
from app.infrastructure.inference.gemini_inference_adapter import GeminiInferenceAdapter
from app.inference_factory import create_inference_provider
from app.ports.inference_port import InferenceProviderError, InferenceRequest


from app.infrastructure.shared.config import SLM_URL

@patch.dict("os.environ", {}, clear=True)
def test_factory_defaults_to_ollama_provider():
    provider = create_inference_provider()
    assert isinstance(provider, OllamaInferenceAdapter)
    assert provider.endpoint == f"{SLM_URL}/api/generate"


@patch.dict(
    "os.environ",
    {
        "INFERENCE_PROVIDER": "gemini",
        "GEMINI_API_KEY": "secret-key",
        "MODEL_NAME": "gemini-1.5-flash-test",
    },
    clear=True,
)
def test_factory_builds_gemini_provider():
    provider = create_inference_provider()
    assert isinstance(provider, GeminiInferenceAdapter)
    assert provider.api_key == "secret-key"
    assert provider.model == "gemini-1.5-flash-test"


@patch.dict("os.environ", {"INFERENCE_PROVIDER": "unknown_provider"}, clear=True)
def test_factory_rejects_unknown_provider():
    with pytest.raises(InferenceProviderError):
        create_inference_provider()


@patch("app.infrastructure.inference.ollama_inference_adapter.requests.post")
def test_ollama_adapter_generate_returns_normalized_result(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "hello from model"}
    mock_post.return_value = mock_response

    provider = OllamaInferenceAdapter(endpoint="http://localhost:11434/api/generate")
    result = provider.generate(
        InferenceRequest(model="qwen2.5:7b", prompt="hello", stream=False)
    )

    assert result.text == "hello from model"
    assert result.provider == "ollama"
    assert result.latency_seconds >= 0

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["model"] == "qwen2.5:7b"
    assert kwargs["json"]["prompt"] == "hello"


@patch("app.infrastructure.inference.ollama_inference_adapter.requests.post")
def test_ollama_adapter_connection_error_raises_domain_error(mock_post):
    mock_post.side_effect = requests.exceptions.ConnectionError("network down")
    provider = OllamaInferenceAdapter(endpoint="http://localhost:11434/api/generate")

    with pytest.raises(InferenceProviderError):
        provider.generate(InferenceRequest(model="qwen2.5:7b", prompt="hello"))
