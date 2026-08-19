"""Pure domain records for the document-operation runtime.

This module deliberately has no FastAPI, LangChain, Chroma or HTTP imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Source:
    id: str
    filename: str
    media_type: str
    sha256: str
    size_bytes: int
    stored_path: str
    created_at: str = field(default_factory=utcnow)


@dataclass(frozen=True)
class DocumentVersion:
    id: str
    source_id: str
    version: int
    parser: str
    status: Literal["queued", "processing", "ready", "failed"]
    created_at: str = field(default_factory=utcnow)


@dataclass(frozen=True)
class EvidenceUnit:
    id: str
    document_id: str
    content: str
    ordinal: int
    locator: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IngestionJob:
    id: str
    source_id: str
    status: Literal["queued", "processing", "ready", "failed"]
    stage: str
    error: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utcnow)
    updated_at: str = field(default_factory=utcnow)


@dataclass(frozen=True)
class QuerySession:
    id: str
    created_at: str = field(default_factory=utcnow)


@dataclass(frozen=True)
class DerivedArtifact:
    id: str
    document_id: str
    kind: str
    status: str


@dataclass(frozen=True)
class AuditEvent:
    id: str
    event_type: str
    subject_id: str
    payload: dict[str, Any]
    created_at: str = field(default_factory=utcnow)
