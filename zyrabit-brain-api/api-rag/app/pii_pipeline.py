"""PII anonymization with interceptor-based security pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import re


EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
CARD_REGEX = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
AMOUNT_REGEX = re.compile(r"(?:USD|EUR|MXN|\$)\s?\d+(?:,\d{3})*(?:\.\d{2})?")
PHONE_REGEX = re.compile(r"\b(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?){2}\d{4}\b")
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
NAME_CONTEXT_REGEX = re.compile(
    r"\b(?:my name is|i am|i'm|me llamo|mi nombre es)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b"
)

TOKEN_PREFIX = {
    "email": "USER_EMAIL",
    "card": "CARD",
    "amount": "AMOUNT",
    "phone": "PHONE",
    "ssn": "SSN",
    "name": "USER_NAME",
}


@dataclass(frozen=True)
class EntitySpan:
    start: int
    end: int
    label: str
    value: str


@dataclass
class AnonymizationResult:
    sanitized_text: str
    token_map: Dict[str, str]
    detected_entities: Dict[str, int]


@dataclass
class PipelineContext:
    """Shared mutable context through interceptor stages."""

    token_map: Dict[str, str] = field(default_factory=dict)
    detected_entities: Dict[str, int] = field(
        default_factory=lambda: {
            "email": 0,
            "card": 0,
            "amount": 0,
            "phone": 0,
            "ssn": 0,
            "name": 0,
        }
    )


class TextInterceptor(ABC):
    """Request/response interceptor contract."""

    @abstractmethod
    def process_request(self, text: str, context: PipelineContext) -> str:
        raise NotImplementedError

    def process_response(self, text: str, context: PipelineContext) -> str:
        return text


class ShardAnonymizationInterceptor(TextInterceptor):
    """Apply sharded anonymization before model call and restore after."""

    def __init__(self, shard_size: int = 160, overlap: int = 40):
        self.shard_size = shard_size
        self.overlap = overlap

    def process_request(self, text: str, context: PipelineContext) -> str:
        result = _anonymize_with_shards(
            text=text,
            shard_size=self.shard_size,
            overlap=self.overlap,
        )
        context.token_map = result.token_map
        context.detected_entities = result.detected_entities
        return result.sanitized_text

    def process_response(self, text: str, context: PipelineContext) -> str:
        return deanonymize_text(text, context.token_map)


class InterceptorPipeline:
    """Composable interceptor pipeline for secure prompt processing."""

    def __init__(self, interceptors: List[TextInterceptor]):
        self.interceptors = interceptors

    def process_request(self, text: str, context: PipelineContext) -> str:
        output = text
        for interceptor in self.interceptors:
            output = interceptor.process_request(output, context)
        return output

    def process_response(self, text: str, context: PipelineContext) -> str:
        output = text
        for interceptor in reversed(self.interceptors):
            output = interceptor.process_response(output, context)
        return output


def build_default_pipeline(shard_size: int = 160, overlap: int = 40) -> InterceptorPipeline:
    return InterceptorPipeline(
        interceptors=[ShardAnonymizationInterceptor(shard_size=shard_size, overlap=overlap)]
    )


def _is_luhn_valid(number_text: str) -> bool:
    digits = re.sub(r"\D", "", number_text)
    if len(digits) < 13 or len(digits) > 19:
        return False

    total = 0
    reverse_digits = digits[::-1]
    for index, ch in enumerate(reverse_digits):
        value = int(ch)
        if index % 2 == 1:
            value = value * 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def _build_shards(text: str, shard_size: int, overlap: int) -> List[Tuple[int, str]]:
    if not text:
        return []

    stride = max(1, shard_size - overlap)
    shards: List[Tuple[int, str]] = []
    start = 0
    while start < len(text):
        shard = text[start:start + shard_size]
        shards.append((start, shard))
        if start + shard_size >= len(text):
            break
        start += stride
    return shards


def _detect_entities_in_shard(shard_text: str, offset: int) -> List[EntitySpan]:
    entities: List[EntitySpan] = []

    for match in EMAIL_REGEX.finditer(shard_text):
        entities.append(
            EntitySpan(
                start=offset + match.start(),
                end=offset + match.end(),
                label="email",
                value=match.group(0),
            )
        )

    for match in CARD_REGEX.finditer(shard_text):
        candidate = match.group(0)
        if _is_luhn_valid(candidate):
            entities.append(
                EntitySpan(
                    start=offset + match.start(),
                    end=offset + match.end(),
                    label="card",
                    value=candidate,
                )
            )

    for match in AMOUNT_REGEX.finditer(shard_text):
        entities.append(
            EntitySpan(
                start=offset + match.start(),
                end=offset + match.end(),
                label="amount",
                value=match.group(0),
            )
        )

    for match in PHONE_REGEX.finditer(shard_text):
        entities.append(
            EntitySpan(
                start=offset + match.start(),
                end=offset + match.end(),
                label="phone",
                value=match.group(0),
            )
        )

    for match in SSN_REGEX.finditer(shard_text):
        entities.append(
            EntitySpan(
                start=offset + match.start(),
                end=offset + match.end(),
                label="ssn",
                value=match.group(0),
            )
        )

    for match in NAME_CONTEXT_REGEX.finditer(shard_text):
        captured_name = match.group(1)
        start = offset + match.start(1)
        end = offset + match.end(1)
        entities.append(
            EntitySpan(
                start=start,
                end=end,
                label="name",
                value=captured_name,
            )
        )

    return entities


def _dedupe_entities(entities: List[EntitySpan]) -> List[EntitySpan]:
    if not entities:
        return []

    unique: Dict[Tuple[int, int, str], EntitySpan] = {}
    for entity in entities:
        unique[(entity.start, entity.end, entity.label)] = entity
    deduped = list(unique.values())

    # Prefer longest matches to avoid nested overlap replacements.
    deduped.sort(key=lambda item: (-(item.end - item.start), item.start))
    selected: List[EntitySpan] = []
    occupied: List[Tuple[int, int]] = []
    for entity in deduped:
        has_overlap = any(
            not (entity.end <= start or entity.start >= end)
            for start, end in occupied
        )
        if has_overlap:
            continue
        selected.append(entity)
        occupied.append((entity.start, entity.end))

    return sorted(selected, key=lambda item: item.start)


def _anonymize_with_shards(
    text: str,
    shard_size: int = 160,
    overlap: int = 40,
) -> AnonymizationResult:
    shards = _build_shards(text, shard_size=shard_size, overlap=overlap)

    detected: List[EntitySpan] = []
    for offset, shard_text in shards:
        detected.extend(_detect_entities_in_shard(shard_text, offset=offset))

    normalized = _dedupe_entities(detected)
    if not normalized:
        return AnonymizationResult(
            sanitized_text=text,
            token_map={},
            detected_entities={
                "email": 0,
                "card": 0,
                "amount": 0,
                "phone": 0,
                "ssn": 0,
                "name": 0,
            },
        )

    token_map: Dict[str, str] = {}
    entity_counts = {"email": 0, "card": 0, "amount": 0, "phone": 0, "ssn": 0, "name": 0}
    value_to_token: Dict[Tuple[str, str], str] = {}

    output_parts: List[str] = []
    cursor = 0

    for entity in normalized:
        output_parts.append(text[cursor:entity.start])
        key = (entity.label, entity.value)
        token = value_to_token.get(key)
        if token is None:
            entity_counts[entity.label] += 1
            token = f"<{TOKEN_PREFIX[entity.label]}_{entity_counts[entity.label]}>"
            value_to_token[key] = token
            token_map[token] = entity.value
        output_parts.append(token)
        cursor = entity.end

    output_parts.append(text[cursor:])

    return AnonymizationResult(
        sanitized_text="".join(output_parts),
        token_map=token_map,
        detected_entities=entity_counts,
    )


def anonymize_text(text: str, shard_size: int = 160, overlap: int = 40) -> AnonymizationResult:
    """Backward-compatible helper for direct anonymization usage."""
    return _anonymize_with_shards(text=text, shard_size=shard_size, overlap=overlap)


def deanonymize_text(text: str, token_map: Dict[str, str]) -> str:
    if not token_map:
        return text

    output = text
    for token in sorted(token_map.keys(), key=len, reverse=True):
        output = output.replace(token, token_map[token])
    return output
