# ==============================================================================
# TEST RATIONALE (DIRECT OLLAMA EMBEDDINGS ADAPTER)
# ==============================================================================
# Purpose: Lock the real DirectOllamaEmbeddings HTTP contract — timeout budget,
# retries on transport failures, and health that reflects recent embed failures.
# Rationale: A tags-only health check previously reported embeddings ready while
# ingest failed on a hard-coded 5s timeout (#204).
# ==============================================================================

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from app.infrastructure.persistence.chroma_adapter import DirectOllamaEmbeddings


def _ok_response(vectors=None):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"embeddings": vectors or [[0.1, 0.2, 0.3]]}
    response.raise_for_status = MagicMock()
    return response


def _tags_response(model: str = "mxbai-embed-large"):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"models": [{"name": f"{model}:latest"}]}
    response.raise_for_status = MagicMock()
    return response


@patch("app.infrastructure.persistence.chroma_adapter.time.sleep", return_value=None)
@patch("app.infrastructure.persistence.chroma_adapter.requests.post")
def test_embed_uses_configured_timeout_seconds(mock_post, _sleep):
    mock_post.return_value = _ok_response()
    embeddings = DirectOllamaEmbeddings(
        model="mxbai-embed-large",
        base_url="http://zyrabit-engine:11434",
        timeout_seconds=60,
        max_retries=1,
    )

    result = embeddings.embed_query("hello")

    assert result == [0.1, 0.2, 0.3]
    assert mock_post.call_args.kwargs["timeout"] == 60.0


@patch("app.infrastructure.persistence.chroma_adapter.time.sleep", return_value=None)
@patch("app.infrastructure.persistence.chroma_adapter.requests.post")
def test_embed_retries_transient_timeout_then_succeeds(mock_post, mock_sleep):
    mock_post.side_effect = [
        requests.exceptions.Timeout("slow cpu"),
        _ok_response([[0.4, 0.5]]),
    ]
    embeddings = DirectOllamaEmbeddings(
        model="mxbai-embed-large",
        base_url="http://zyrabit-engine:11434",
        timeout_seconds=60,
        max_retries=3,
    )

    result = embeddings.embed_documents(["chunk-a"])

    assert result == [[0.4, 0.5]]
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once()
    # After a timeout retry recovery, tags may still pass but health is degraded.
    with patch(
        "app.infrastructure.persistence.chroma_adapter.requests.get",
        return_value=_tags_response(),
    ):
        ok, detail = embeddings.health()
    assert ok is False
    assert "recovered after timeout retry" in detail


@patch("app.infrastructure.persistence.chroma_adapter.time.sleep", return_value=None)
@patch("app.infrastructure.persistence.chroma_adapter.requests.post")
def test_embed_exhausts_retries_and_marks_health_failed(mock_post, _sleep):
    mock_post.side_effect = requests.exceptions.Timeout("still too slow")
    embeddings = DirectOllamaEmbeddings(
        model="mxbai-embed-large",
        base_url="http://zyrabit-engine:11434",
        timeout_seconds=60,
        max_retries=3,
    )

    with pytest.raises(RuntimeError, match="Embedding provider unavailable"):
        embeddings.embed_query("hello")

    assert mock_post.call_count == 3
    with patch(
        "app.infrastructure.persistence.chroma_adapter.requests.get",
        return_value=_tags_response(),
    ):
        ok, detail = embeddings.health()
    assert ok is False
    assert "recent embedding failure" in detail
    assert "Timeout" in detail


@patch("app.infrastructure.persistence.chroma_adapter.requests.get")
@patch("app.infrastructure.persistence.chroma_adapter.requests.post")
def test_clean_success_clears_failure_and_reports_ready(mock_post, mock_get):
    embeddings = DirectOllamaEmbeddings(
        model="mxbai-embed-large",
        base_url="http://zyrabit-engine:11434",
        timeout_seconds=60,
        max_retries=1,
    )
    embeddings._last_failure_detail = "Timeout: prior"
    mock_post.return_value = _ok_response()
    mock_get.return_value = _tags_response()

    embeddings.embed_query("hello")
    ok, detail = embeddings.health()

    assert ok is True
    assert "mxbai-embed-large available" in detail
    assert "last embed" in detail


@patch("app.infrastructure.persistence.chroma_adapter.requests.get")
def test_tags_only_ready_when_no_recent_failure(mock_get):
    mock_get.return_value = _tags_response()
    embeddings = DirectOllamaEmbeddings(
        model="mxbai-embed-large",
        base_url="http://zyrabit-engine:11434",
        timeout_seconds=60,
    )

    ok, detail = embeddings.health()

    assert ok is True
    assert detail == "mxbai-embed-large available"


@patch("app.infrastructure.persistence.chroma_adapter.time.sleep", return_value=None)
@patch("app.infrastructure.persistence.chroma_adapter.requests.post")
def test_batch_size_is_honored(mock_post, _sleep):
    mock_post.return_value = _ok_response([[0.1], [0.2]])
    embeddings = DirectOllamaEmbeddings(
        model="mxbai-embed-large",
        base_url="http://zyrabit-engine:11434",
        timeout_seconds=60,
        batch_size=2,
        max_retries=1,
    )

    embeddings.embed_documents(["a", "b", "c"])

    assert mock_post.call_count == 2
    first_batch = mock_post.call_args_list[0].kwargs["json"]["input"]
    second_batch = mock_post.call_args_list[1].kwargs["json"]["input"]
    assert first_batch == ["a", "b"]
    assert second_batch == ["c"]
