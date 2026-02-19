from app.security import anonymize_text, deanonymize_text, sanitize_pii


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
