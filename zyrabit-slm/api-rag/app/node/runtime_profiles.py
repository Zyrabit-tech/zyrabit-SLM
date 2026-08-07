"""Declarative runtime profiles; credentials and endpoints remain in environment variables."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RuntimeProfile:
    name: str
    generator: str
    embedding: str
    reranker: str | None
    expected_memory_gb: int
    description: str


PROFILES = {
    "local-minimal": RuntimeProfile("local-minimal", "qwen2.5:1.5b", "nomic-embed-text", None, 8, "Low-memory local document Q&A."),
    "local-balanced": RuntimeProfile("local-balanced", "qwen3:4b", "qwen3-embedding:0.6b", "bge-reranker-v2-m3", 16, "Recommended local quality profile."),
    "local-performance": RuntimeProfile("local-performance", "qwen3:8b", "qwen3-embedding:4b", "bge-reranker-v2-m3", 32, "Higher quality profile for capable hardware."),
}


def profile_payload(name: str) -> dict:
    return asdict(PROFILES[name])
