"""Prometheus metrics helpers for Zyrabit API."""

from __future__ import annotations

import os
import re

from prometheus_client import Counter, Histogram


TOKEN_LATENCY_MS_PER_TOKEN = Histogram(
    "zyrabit_token_latency_ms_per_token",
    "Model latency in milliseconds per generated token.",
    buckets=(0.1, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500),
)

TOKEN_USAGE_TOTAL = Counter(
    "zyrabit_token_usage_total",
    "Token usage counters for input, output and estimated cloud savings.",
    ["direction"],
)

SECURITY_HITS_TOTAL = Counter(
    "zyrabit_security_hits_total",
    "PII detection counters by entity type.",
    ["entity_type"],
)

_TOKEN_SAVINGS_MULTIPLIER = float(os.getenv("TOKEN_SAVINGS_MULTIPLIER", "1.3"))


def approximate_token_count(text: str) -> int:
    """Approximate token count without model-specific tokenizer dependency."""
    if not text:
        return 0
    return len(re.findall(r"\w+|[^\w\s]", text))


def observe_security_hits(entity_hits: dict) -> None:
    for entity, count in entity_hits.items():
        if count > 0:
            SECURITY_HITS_TOTAL.labels(entity_type=entity).inc(count)


def observe_token_usage(input_tokens: int, output_tokens: int) -> None:
    TOKEN_USAGE_TOTAL.labels(direction="input").inc(max(input_tokens, 0))
    TOKEN_USAGE_TOTAL.labels(direction="output").inc(max(output_tokens, 0))

    current = max(input_tokens, 0) + max(output_tokens, 0)
    estimated_cloud = int(current * _TOKEN_SAVINGS_MULTIPLIER)
    saved = max(estimated_cloud - current, 0)
    TOKEN_USAGE_TOTAL.labels(direction="saved_vs_cloud").inc(saved)


def observe_latency_per_token(latency_seconds: float, output_tokens: int) -> None:
    if latency_seconds <= 0:
        return
    safe_output = max(output_tokens, 1)
    latency_ms_per_token = (latency_seconds * 1000.0) / safe_output
    TOKEN_LATENCY_MS_PER_TOKEN.observe(latency_ms_per_token)
