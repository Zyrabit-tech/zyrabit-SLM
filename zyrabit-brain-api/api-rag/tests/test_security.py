import pytest
# Importamos la función desde nuestro nuevo módulo
from app.security import sanitize_pii

def test_sanitize_email():
    input_text = "Por favor contactar a ceo@zyrabit.com para el contrato."
    clean_text, was_changed = sanitize_pii(input_text)
    
    assert was_changed is True
    assert "ceo@zyrabit.com" not in clean_text
    assert "[EMAIL_REDACTED]" in clean_text

def test_sanitize_credit_card():
    # Caso con espacios y guiones
    input_text = "Cobrar a la tarjeta 4152-3131-2341-1123 inmediatamente."
    clean_text, was_changed = sanitize_pii(input_text)
    
    assert was_changed is True
    assert "4152" not in clean_text
    assert "[CREDIT_CARD_REDACTED]" in clean_text

def test_sanitize_amount():
    input_text = "Transferir $50,000.00 USD a la cuenta."
    clean_text, was_changed = sanitize_pii(input_text)
    
    assert was_changed is True
    assert "$50,000.00" not in clean_text
    assert "[AMOUNT_REDACTED]" in clean_text

def test_no_pii_safe_text():
    input_text = "¿Cuál es la capital de Francia?"
    clean_text, was_changed = sanitize_pii(input_text)
    
    assert was_changed is False
    assert clean_text == input_text

def test_mixed_content():
    input_text = "El usuario admin@test.com pagó $100 con la tarjeta 1234 5678 1234 5678."
    clean_text, _ = sanitize_pii(input_text)
    
    assert "[EMAIL_REDACTED]" in clean_text
    assert "[AMOUNT_REDACTED]" in clean_text
    assert "[CREDIT_CARD_REDACTED]" in clean_text
