"""Centralized security helpers for anonymization and interceptor pipelines."""

from typing import Dict, Tuple

from .security.pii_pipeline import AnonymizationResult, anonymize_text as _anonymize_text
from .security.pii_pipeline import (
    InterceptorPipeline,
    PipelineContext,
    build_default_pipeline,
)
from .security.pii_pipeline import deanonymize_text as _deanonymize_text


def anonymize_text(text: str) -> AnonymizationResult:
    """Return anonymized text and reversible token map."""
    return _anonymize_text(text)


def deanonymize_text(text: str, token_map: Dict[str, str]) -> str:
    """Restore original entities in text using token_map."""
    return _deanonymize_text(text, token_map)


def sanitize_pii(text: str) -> Tuple[str, bool]:
    """Backward-compatible API used by existing callers/tests."""
    result = _anonymize_text(text)
    return result.sanitized_text, bool(result.token_map)


def build_security_pipeline(shard_size: int = 160, overlap: int = 40) -> InterceptorPipeline:
    return build_default_pipeline(shard_size=shard_size, overlap=overlap)


__all__ = [
    "anonymize_text",
    "deanonymize_text",
    "sanitize_pii",
    "build_security_pipeline",
    "PipelineContext",
    "InterceptorPipeline",
    "AnonymizationResult",
]
