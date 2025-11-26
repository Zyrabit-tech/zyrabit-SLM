import re
from typing import Tuple

# Patrones de Regex Compilados (Mejor rendimiento)
EMAIL_REGEX = re.compile(r'[\w\.-]+@[\w\.-]+')
CREDIT_CARD_REGEX = re.compile(r'\b(?:\d[ -]*?){13,16}\b')
# Detecta formatos como $50,000.00, 500 USD, $50k
AMOUNT_REGEX = re.compile(r'\$?\d+(?:,\d{3})*(?:\.\d{2})? ?(?:USD|MXN|EUR|k)?')

def sanitize_pii(text: str) -> Tuple[str, bool]:
    """
    Sanitiza información personal identificable (PII) del texto.
    
    Args:
        text (str): El texto de entrada (prompt).
        
    Returns:
        Tuple[str, bool]: (Texto sanitizado, Bool indicando si hubo cambios)
    """
    if not text:
        return "", False

    original_text = text
    
    # 1. Sanitizar Emails
    text = EMAIL_REGEX.sub('[EMAIL_REDACTED]', text)
    
    # 2. Sanitizar Tarjetas de Crédito
    text = CREDIT_CARD_REGEX.sub('[CREDIT_CARD_REDACTED]', text)
    
    # 3. Sanitizar Montos (Opcional: a veces el monto es contexto útil, pero para demos financieras lo quitamos)
    # Nota: Ajustamos para no borrar números simples, solo los que parecen dinero
    text = AMOUNT_REGEX.sub('[AMOUNT_REDACTED]', text)

    is_sanitized = text != original_text
    return text, is_sanitized
