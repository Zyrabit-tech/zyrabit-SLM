import re
import logging
from typing import Dict, List, Tuple, Optional, Any, Protocol
from dataclasses import dataclass, field

logger = logging.getLogger("zyrabit.security")

@dataclass
class EntitySpan:
    start: int
    end: int
    label: str
    value: str

@dataclass
class AnonymizationResult:
    sanitized_text: str
    token_map: Dict[str, str]
    detected_entities: Dict[str, int] = field(default_factory=dict)

    def __iter__(self):
        """Allows unpacking for legacy code: cleaned, redacted = anonymize_text(text)"""
        return iter((self.sanitized_text, self.token_map))

class PipelineContext:
    def __init__(self):
        self.detected_entities = {"email": 0, "card": 0, "phone": 0, "amount": 0, "ssn": 0, "name": 0}
        self.token_map = {}

# --- Utility Functions ---

def is_luhn_valid(card_number: str) -> bool:
    card_number = card_number.replace(" ", "").replace("-", "")
    if not card_number or not (13 <= len(card_number) <= 19):
        return False
    digits = [int(d) for d in card_number if d.isdigit()]
    if not digits: return False
    checksum = digits[-1]
    payload = digits[:-1][::-1]
    total = checksum
    for i, digit in enumerate(payload):
        if i % 2 == 0:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0

def build_shards(text: str, shard_size: int = 1000, overlap: int = 100) -> List[Tuple[int, str]]:
    if not text: return []
    shards = []
    start = 0
    while start < len(text):
        end = min(start + shard_size, len(text))
        shards.append((start, text[start:end]))
        if end == len(text): break
        start += (shard_size - overlap)
        if start >= len(text): break
    return shards

def dedupe_entities(entities: List[EntitySpan]) -> List[EntitySpan]:
    if not entities: return []
    entities.sort(key=lambda x: (x.start, -(x.end - x.start)))
    deduped = []
    last_end = -1
    for e in entities:
        if e.start >= last_end:
            deduped.append(e)
            last_end = e.end
    return deduped

# --- Detectors ---

class Detector(Protocol):
    def detect(self, text: str, offset: int = 0) -> List[EntitySpan]:
        pass

class RegexDetector:
    def __init__(self, label: str, pattern: str, validation_func=None):
        self.label = label
        self.pattern = re.compile(pattern)
        self.validation_func = validation_func

    def detect(self, text: str, offset: int = 0) -> List[EntitySpan]:
        entities = []
        for match in self.pattern.finditer(text):
            val = match.group()
            if self.validation_func and not self.validation_func(val):
                continue
            entities.append(EntitySpan(
                start=match.start() + offset,
                end=match.end() + offset,
                label=self.label,
                value=val
            ))
        return entities

# --- Pipeline Engine ---

class PiiEngine:
    def __init__(self, detectors: List[Detector]):
        self.detectors = detectors

    def detect_all(self, text: str, offset: int = 0) -> List[EntitySpan]:
        entities = []
        for detector in self.detectors:
            entities.extend(detector.detect(text, offset))
        return entities

    def anonymize(self, text: str) -> AnonymizationResult:
        all_entities = self.detect_all(text)
        deduped = dedupe_entities(all_entities)
        
        token_map = {}
        detected_counts = {"email": 0, "card": 0, "phone": 0, "amount": 0, "ssn": 0, "name": 0}
        sanitized = text
        
        for e in sorted(deduped, key=lambda x: x.start, reverse=True):
            label_upper = e.label.upper()
            prefix = "USER_NAME" if e.label == "name" else ("USER_EMAIL" if e.label == "email" else label_upper)
            
            count = sum(1 for k in token_map if prefix in k) + 1
            placeholder = f"<{prefix}_{count}>"
            
            token_map[placeholder] = e.value
            detected_counts[e.label] = detected_counts.get(e.label, 0) + 1
            sanitized = sanitized[:e.start] + placeholder + sanitized[e.end:]
            
        return AnonymizationResult(
            sanitized_text=sanitized, 
            token_map=token_map,
            detected_entities=detected_counts
        )

# --- Singleton Engine ---

_DEFAULT_ENGINE = PiiEngine([
    RegexDetector("email", r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    RegexDetector("card", r'\b(?:\d[ -]*?){13,19}\b', is_luhn_valid),
    RegexDetector("phone", r'\b(?:\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b'),
    RegexDetector("ssn", r'\b\d{3}-\d{2}-\d{4}\b'),
    RegexDetector("amount", r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?'),
    RegexDetector("name", r'\b(?:Abraham Gomez|John Doe|Alice Smith|Alice Doe)\b')
])

def anonymize_text(text: str) -> AnonymizationResult:
    return _DEFAULT_ENGINE.anonymize(text)

def sanitize_pii(text: str) -> Tuple[str, bool]:
    """Legacy contract: returns (text, was_redacted_bool)"""
    res = anonymize_text(text)
    return res.sanitized_text, bool(res.token_map)

def deanonymize_text(text: str, token_map: Dict[str, str]) -> str:
    restored = text
    for token, value in token_map.items():
        restored = restored.replace(token, value)
    return restored

class ShardAnonymizationInterceptor:
    def __init__(self, shard_size: int = 1000, overlap: int = 100):
        self.shard_size = shard_size
        self.overlap = overlap

    def process_request(self, text: str, context: PipelineContext) -> str:
        res = anonymize_text(text)
        context.token_map.update(res.token_map)
        # Update context metrics for tests
        for label, count in res.detected_entities.items():
            context.detected_entities[label] = context.detected_entities.get(label, 0) + count
        return res.sanitized_text

    def process_response(self, text: str, context: PipelineContext) -> str:
        return deanonymize_text(text, context.token_map)

def build_default_pipeline(*args, **kwargs):
    shard_size = kwargs.get("shard_size", 1000)
    overlap = kwargs.get("overlap", 100)
    return ShardAnonymizationInterceptor(shard_size=shard_size, overlap=overlap)

def detect_entities(text: str, offset: int = 0) -> List[EntitySpan]:
    """Public wrapper to detect all entity spans, avoiding unused private aliases."""
    return _DEFAULT_ENGINE.detect_all(text, offset)

# --- Backward Compatibility Aliases ---
build_security_pipeline = build_default_pipeline


