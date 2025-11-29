import pytest
from app.security import sanitize_pii

@pytest.mark.parametrize(
    "input_text,expected_output,expected_redacted",
    [
        ("Contact me at user@example.com", "Contact me at ████████", True),
        ("My card 4111-1111-1111-1111 is valid", "My card [CREDIT_CARD] is valid", True),
        ("Amount due: $1,234.56", "Amount due: [AMOUNT]", True),
        ("No sensitive data here.", "No sensitive data here.", False),
        ("Mixed 1234 5678 9012 3456 and $99.99", "Mixed [CREDIT_CARD] and [AMOUNT]", True),
    ],
)
def test_sanitize_pii(input_text, expected_output, expected_redacted):
    cleaned, redacted = sanitize_pii(input_text)
    assert cleaned == expected_output
    assert redacted == expected_redacted
