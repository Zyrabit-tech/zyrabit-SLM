import pytest
from app.pii_pipeline import (
    anonymize_text,
    deanonymize_text,
    _is_luhn_valid,
    _build_shards,
    _detect_entities_in_shard,
    _dedupe_entities,
    build_default_pipeline,
    PipelineContext,
    EntitySpan,
    ShardAnonymizationInterceptor
)

def test_luhn_validity():
    # Valid credit card numbers algorithms check
    assert _is_luhn_valid("4242424242424242") == True
    assert _is_luhn_valid("49927398717") == False
    assert _is_luhn_valid("1234") == False  # Too short < 13
    assert _is_luhn_valid("123456789012345678901") == False # Too long > 19

def test_build_shards():
    text = "A" * 200
    shards = _build_shards(text, shard_size=160, overlap=40)
    assert len(shards) == 2
    assert shards[0][0] == 0
    assert len(shards[0][1]) == 160
    assert shards[1][0] == 120  # stride is 160-40 = 120
    assert len(shards[1][1]) == 80  # the remaining part text is length 200 (120 to 200 = 80 chars)

    # Empty text
    assert _build_shards("", 160, 40) == []

def test_detect_entities_in_shard():
    text = "My name is John Doe, email john@example.com, card 4242424242424242 phone 123-456-7890 amount $1,000 ssn 123-45-6789"
    entities = _detect_entities_in_shard(text, offset=0)
    
    label_set = {e.label for e in entities}
    assert "email" in label_set
    assert "card" in label_set
    assert "phone" in label_set
    assert "amount" in label_set
    assert "ssn" in label_set
    assert "name" in label_set

def test_dedupe_entities():
    # Overlapping entities testing longest match wins
    e1 = EntitySpan(start=0, end=10, label="amount", value="$1,000,000")
    e2 = EntitySpan(start=2, end=8, label="amount", value="1,000")
    
    deduped = _dedupe_entities([e1, e2])
    assert len(deduped) == 1
    assert deduped[0].value == "$1,000,000"

    # Empty dedupe
    assert _dedupe_entities([]) == []

def test_anonymize_text_and_deanonymize():
    original = "My name is Abraham Gomez. My email is abraham@example.com."
    result = anonymize_text(original)
    
    # Check that placeholders are inserted
    assert "<USER_NAME_1>" in result.sanitized_text
    assert "<USER_EMAIL_1>" in result.sanitized_text
    assert "Abraham Gomez" not in result.sanitized_text
    assert "abraham@example.com" not in result.sanitized_text

    # Reconstruct
    restored = deanonymize_text(result.sanitized_text, result.token_map)
    assert restored == original

def test_anonymize_text_empty():
    res = anonymize_text("just normal text without entities")
    assert res.sanitized_text == "just normal text without entities"
    assert not res.token_map
    
def test_deanonymize_empty_token_map():
    assert deanonymize_text("text", {}) == "text"

def test_pipeline_interceptor():
    pipeline = build_default_pipeline()
    context = PipelineContext()
    
    original = "Please charge $500 to my card 4242424242424242."
    sanitized = pipeline.process_request(original, context)
    
    assert "<AMOUNT_1>" in sanitized
    assert "<CARD_1>" in sanitized
    assert "4242424242424242" not in sanitized
    
    restored = pipeline.process_response(sanitized, context)
    assert restored == original

def test_shard_anonymization_interceptor():
    interceptor = ShardAnonymizationInterceptor(shard_size=10, overlap=2)
    context = PipelineContext()
    text = "email test@test.com" # Length 19
    sanitized = interceptor.process_request(text, context)
    assert "<USER_EMAIL_1>" in sanitized
    restored = interceptor.process_response(sanitized, context)
    assert restored == text
    
def test_pipeline_context_init():
    ctx = PipelineContext()
    assert ctx.detected_entities["email"] == 0
    assert isinstance(ctx.token_map, dict)
