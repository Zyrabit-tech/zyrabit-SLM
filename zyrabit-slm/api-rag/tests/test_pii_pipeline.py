from app.core.security.pii_pipeline import (
    anonymize_text,
    deanonymize_text,
    is_luhn_valid,
    is_curp_valid,
    is_rfc_valid,
    is_clabe_valid,
    build_shards,
    detect_entities,
    dedupe_entities,
    build_default_pipeline,
    PipelineContext,
    EntitySpan,
    ShardAnonymizationInterceptor
)

def test_mexico_identifier_checksums_and_masking():
    valid_curp = "ROMC800514HDFXXX01"
    valid_rfc_persona_fisica = "GODE561231GR8"
    valid_rfc_persona_moral = "XEXX010101000"
    valid_clabe = "032180000118359719"

    assert is_curp_valid(valid_curp)
    assert is_rfc_valid(valid_rfc_persona_fisica)
    assert is_rfc_valid(valid_rfc_persona_moral)
    assert is_clabe_valid(valid_clabe)

    text = f"CURP {valid_curp}, RFC {valid_rfc_persona_fisica}/{valid_rfc_persona_moral}, CLABE {valid_clabe}"
    result = anonymize_text(text)
    assert "<CURP_1>" in result.sanitized_text
    assert "<RFC_1>" in result.sanitized_text
    assert "<RFC_2>" in result.sanitized_text
    assert "<CLABE_1>" in result.sanitized_text
    assert deanonymize_text(result.sanitized_text, result.token_map) == text


def test_invalid_mexico_checksums_are_not_masked():
    invalid_curp = "ROMC800514HDFXXX00"
    invalid_rfc = "GODE561231GR7"
    invalid_clabe = "032180000118359718"

    assert not is_curp_valid(invalid_curp)
    assert not is_rfc_valid(invalid_rfc)
    assert not is_clabe_valid(invalid_clabe)
    assert not is_luhn_valid(invalid_clabe)

    text = f"{invalid_curp} {invalid_rfc} {invalid_clabe}"
    result = anonymize_text(text)
    assert result.sanitized_text == text
    assert result.token_map == {}


def test_luhn_validity():
    # Valid credit card numbers algorithms check
    assert is_luhn_valid("4242424242424242")
    assert not is_luhn_valid("49927398717")
    assert not is_luhn_valid("1234")  # Too short < 13
    assert not is_luhn_valid("123456789012345678901") # Too long > 19


def test_18_digit_card_and_clabe_checksum_precedence():
    card_only = "032180000118359715"
    both_valid = "000000000000000000"
    assert is_luhn_valid(card_only) and not is_clabe_valid(card_only)
    assert is_luhn_valid(both_valid) and is_clabe_valid(both_valid)

    text = f"card {card_only} CLABE {both_valid}"
    result = anonymize_text(text)
    assert result.sanitized_text == "card <CARD_1> CLABE <CLABE_1>"
    assert deanonymize_text(result.sanitized_text, result.token_map) == text


def test_standalone_phone_and_card_still_mask():
    text = "phone 123-456-7890 card 4242424242424242"
    result = anonymize_text(text)
    assert "<PHONE_1>" in result.sanitized_text
    assert "<CARD_1>" in result.sanitized_text
    assert deanonymize_text(result.sanitized_text, result.token_map) == text


def test_build_shards():
    text = "A" * 200
    shards = build_shards(text, shard_size=160, overlap=40)
    assert len(shards) == 2
    assert shards[0][0] == 0
    assert len(shards[0][1]) == 160
    assert shards[1][0] == 120  # stride is 160-40 = 120
    assert len(shards[1][1]) == 80  # the remaining part text is length 200 (120 to 200 = 80 chars)

    # Empty text
    assert build_shards("", 160, 40) == []

def test_detect_entities_in_shard():
    text = "My name is John Doe, email john@example.com, card 4242424242424242 phone 123-456-7890 amount $1,000 ssn 123-45-6789"
    entities = detect_entities(text, offset=0)
    
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
    
    deduped = dedupe_entities([e1, e2])
    assert len(deduped) == 1
    assert deduped[0].value == "$1,000,000"

    # Empty dedupe
    assert dedupe_entities([]) == []

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
