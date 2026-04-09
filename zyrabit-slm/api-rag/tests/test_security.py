from app.core.security import (
    PipelineContext,
    anonymize_text,
    build_security_pipeline,
    deanonymize_text,
    sanitize_pii,
)


def test_sanitize_pii_legacy_contract():
    text = "My email is user@example.com and amount is $9,999.99"
    cleaned, redacted = sanitize_pii(text)
    assert redacted is True
    assert "<USER_EMAIL_1>" in cleaned
    assert "<AMOUNT_1>" in cleaned


def test_anonymize_and_deanonymize_roundtrip():
    prompt = (
        "My name is John Doe and my email is john.doe@example.com. "
        "Card 4111-1111-1111-1111 has amount $1,234.56."
    )
    result = anonymize_text(prompt)
    assert result.detected_entities["name"] == 1
    assert result.detected_entities["email"] == 1
    assert result.detected_entities["card"] == 1
    assert result.detected_entities["amount"] == 1
    assert "john.doe@example.com" not in result.sanitized_text
    assert "4111-1111-1111-1111" not in result.sanitized_text

    model_response = (
        "Sure <USER_NAME_1>, I will send confirmation to <USER_EMAIL_1> "
        "for <AMOUNT_1>."
    )
    restored = deanonymize_text(model_response, result.token_map)
    assert "John Doe" in restored
    assert "john.doe@example.com" in restored
    assert "$1,234.56" in restored


def test_interceptor_pipeline_request_and_response():
    pipeline = build_security_pipeline(shard_size=120, overlap=20)
    context = PipelineContext()
    prompt = "My name is Alice Doe and my email is alice@example.com"
    sanitized = pipeline.process_request(prompt, context)

    assert "<USER_NAME_1>" in sanitized
    assert "<USER_EMAIL_1>" in sanitized
    assert context.detected_entities["name"] == 1
    assert context.detected_entities["email"] == 1

    masked_response = "Thanks <USER_NAME_1>, we will reach <USER_EMAIL_1>."
    restored = pipeline.process_response(masked_response, context)
    assert "Alice Doe" in restored
    assert "alice@example.com" in restored


def test_phone_and_ssn_are_anonymized():
    text = "Contact +1 (415) 555-1234, SSN 123-45-6789"
    result = anonymize_text(text)
    assert "<PHONE_1>" in result.sanitized_text
    assert "<SSN_1>" in result.sanitized_text
    assert result.detected_entities["phone"] == 1
    assert result.detected_entities["ssn"] == 1
