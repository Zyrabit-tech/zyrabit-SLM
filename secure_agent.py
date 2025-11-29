#!/usr/bin/env python3

"""secure_agent.py - CLI client for Zyrabit LLM Secure Suite

Reads a prompt from the command line (or stdin), sanitizes any PII using the same
logic as the central security module, sends the sanitized prompt to the backend
API (`http://localhost:8080/v1/chat`) and prints the original prompt, the sanitized
prompt and the model response.
"""

import os
import sys
import re
import json
import time
import argparse
import requests

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8080/v1/chat")
MODEL_NAME = os.getenv("MODEL_NAME", "phi3")

# Simple PII sanitization (stand‑alone version)
EMAIL_REGEX = re.compile(r"[\w\.-]+@[\w\.-]+")
CREDIT_CARD_REGEX = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
AMOUNT_REGEX = re.compile(r"\$\d+(?:,\d{3})*(?:\.\d{2})?")


def sanitize_pii(text: str) -> (str, bool):
    """Redact email, credit‑card numbers and monetary amounts.
    Returns the cleaned text and a flag indicating whether any redaction occurred.
    """
    original = text
    text = EMAIL_REGEX.sub("████████", text)
    text = CREDIT_CARD_REGEX.sub("[CREDIT_CARD]", text)
    text = AMOUNT_REGEX.sub("[AMOUNT]", text)
    changed = text != original
    return text, changed


def query_backend(prompt: str) -> (str, float):
    payload = {"text": prompt}
    start = time.time()
    try:
        response = requests.post(API_URL, json=payload)
        elapsed = time.time() - start
        if response.status_code == 200:
            data = response.json()
            return data.get("response", ""), elapsed
        else:
            return f"Error del servidor: {response.status_code}", elapsed
    except Exception as e:
        return f"Error de conexión: {str(e)}", 0.0


def main():
    parser = argparse.ArgumentParser(description="Secure agent for Zyrabit LLM")
    parser.add_argument("prompt", nargs="?", help="Prompt to send to the model")
    args = parser.parse_args()

    if args.prompt:
        user_input = args.prompt
    else:
        print("Introduce tu consulta (Ctrl‑D para terminar):")        
        user_input = sys.stdin.read().strip()

    if not user_input:
        print("No se recibió ninguna entrada.")
        sys.exit(1)

    print(f"\n🧩 Prompt original: {user_input}\n")
    clean_prompt, redacted = sanitize_pii(user_input)
    if redacted:
        print(f"🔐 Prompt sanitizado: {clean_prompt}\n")
    else:
        print("🔐 No se detectó PII para sanitizar.\n")

    response, latency = query_backend(clean_prompt)
    print(f"🤖 Respuesta del modelo (latencia {latency:.2f}s):\n{response}\n")


if __name__ == "__main__":
    main()
