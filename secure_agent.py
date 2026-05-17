#!/usr/bin/env python3

"""secure_agent.py - CLI client for Zyrabit SLM Secure Suite

Reads a prompt from the command line (or stdin), sanitizes any PII using the same
logic as the central security module, sends the sanitized prompt to the backend
API (`http://localhost:8080/v1/chat`) and prints the original prompt, the sanitized
prompt and the model response.
"""

import os
import sys
import time
import argparse
try:
    import requests
    import urllib3
except ImportError:
    import sys as _sys
    print(
        "❌ Missing dependencies. Activate the virtual environment first:\n"
        "\n"
        "    source .venv/bin/activate\n"
        "    python3 secure_agent.py \"your prompt here\"\n"
    )
    _sys.exit(1)


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8080/v1/chat")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:7b")
VERIFY_TLS = os.getenv("VERIFY_TLS", "false").lower() == "true"

# Shared security pipeline from backend package.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_PATH = os.path.join(CURRENT_DIR, "zyrabit-slm", "api-rag")
sys.path.append(BACKEND_PATH)
from app.core.security import PipelineContext, build_security_pipeline  # noqa: E402


def query_secure_slm(prompt: str) -> (str, float):
    payload = {"text": prompt}
    start = time.time()
    try:
        response = requests.post(API_URL, json=payload, verify=VERIFY_TLS)
        elapsed = time.time() - start
        if response.status_code == 200:
            data = response.json()
            return data.get("response", ""), elapsed
        else:
            return f"Error del servidor: {response.status_code}", elapsed
    except Exception as e:
        return f"Error de conexión: {str(e)}", 0.0


def main():
    parser = argparse.ArgumentParser(description="Secure agent for Zyrabit SLM")
    parser.add_argument("prompt", nargs="?", help="Prompt to send to the SLM")
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
    pipeline = build_security_pipeline()
    pipeline_context = PipelineContext()
    clean_prompt = pipeline.process_request(user_input, pipeline_context)
    if pipeline_context.token_map:
        print(f"🔐 Prompt sanitizado: {clean_prompt}\n")
    else:
        print("🔐 No se detectó PII para sanitizar.\n")

    response, latency = query_secure_slm(clean_prompt)
    restored_response = pipeline.process_response(response, pipeline_context)
    print(f"🤖 Respuesta del SLM (latencia {latency:.2f}s):\n{restored_response}\n")


if __name__ == "__main__":
    main()
