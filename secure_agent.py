import re
import requests
import json
import sys

# Configuration
MODEL = "phi3"
OLLAMA_URL = "http://localhost:11434/api/generate"

class SecureAgent:
    def __init__(self):
        # Regex patterns for PII (Personally Identifiable Information)
        self.patterns = {
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'PHONE': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'CREDIT_CARD': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            'SSN': r'\b\d{3}-\d{2}-\d{4}\b'
        }

    def sanitize_input(self, text):
        """Redacts sensitive information from the text."""
        redacted_text = text
        for label, pattern in self.patterns.items():
            redacted_text = re.sub(pattern, f"[{label}_REDACTED]", redacted_text)
        return redacted_text

    def query_ollama(self, prompt):
        """Sends the sanitized prompt to Ollama."""
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
        try:
            response = requests.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            return response.json().get('response', '')
        except requests.exceptions.RequestException as e:
            return f"Error conectando con Ollama: {e}"

    def run(self):
        print(f"--- Zyrabit Secure Agent (Model: {MODEL}) ---")
        print("Escribe tu prompt (o 'exit' para salir):")
        
        while True:
            user_input = input("\n> ")
            if user_input.lower() in ['exit', 'quit']:
                break

            # 1. Sanitization
            safe_prompt = self.sanitize_input(user_input)
            
            if safe_prompt != user_input:
                print(f"\n[SEGURIDAD] PII Detectado. Prompt Sanitizado:\n{safe_prompt}")
            else:
                print("\n[SEGURIDAD] No se detectó PII. Enviando prompt limpio...")

            # 2. LLM Query
            print(f"\n[AGENT] Consultando a {MODEL}...")
            response = self.query_ollama(safe_prompt)
            
            # 3. Response
            print(f"\n[RESPUESTA]:\n{response}")

if __name__ == "__main__":
    agent = SecureAgent()
    agent.run()
