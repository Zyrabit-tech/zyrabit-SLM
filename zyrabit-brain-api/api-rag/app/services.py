import os
import time

import requests

from .metrics import (
    approximate_token_count,
    observe_latency_per_token,
    observe_security_hits,
    observe_token_usage,
)
from .security import PipelineContext, build_security_pipeline

# --- CONFIGURATION ---
# Use environment variables or default to local settings
SLM_URL = os.getenv("SLM_URL", "http://slm-engine:11434/api/generate")
# Defaulting to phi3 as per setup script, but overridable
MODEL_NAME = os.getenv("MODEL_NAME", "phi3")

# --- SYSTEM PROMPT LOADING ---
def load_system_prompt() -> str:
    """Loads the system prompt from the txt file.
    
    Returns:
        str: The system prompt content, or empty string if file not found.
    """
    prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"⚠️  WARNING: system_prompt.txt not found at {prompt_path}")
        return ""

# Load system prompt once at module initialization
SYSTEM_PROMPT = load_system_prompt()

def print_header(title: str):
    """Prints a styled header to the console."""
    print(f"\n{'='*60}")
    print(f"🛡️ ZYRABIT SECURITY LAYER: {title}")
    print(f"{'='*60}")

def query_secure_slm(prompt: str) -> tuple[str, float]:
    """
    Sends a sanitized prompt to the local SLM and returns the response and latency.
    
    Args:
        prompt (str): The user's input prompt.
        
    Returns:
        tuple[str, float]: A tuple containing the (response_text, latency_in_seconds).
    """
    # PHASE A: SANITIZATION (Interceptor pipeline)
    pipeline = build_security_pipeline()
    pipeline_context = PipelineContext()
    sanitized_prompt = pipeline.process_request(prompt, pipeline_context)
    observe_security_hits(pipeline_context.detected_entities)

    if pipeline_context.token_map:
        print(f"   ⚠️  THREAT DETECTED. DATA REDACTED.")
        print(f"   SENT:     {sanitized_prompt}")
    else:
        print("   ✅ Input clean. Forwarding to core.")

    # PHASE B: LOCAL INFERENCE (Air-Gapped)
    # Construct prompt with system context
    full_prompt = f"{SYSTEM_PROMPT}\n\nUser: {sanitized_prompt}\nAssistant:" if SYSTEM_PROMPT else sanitized_prompt
    
    payload = {
        "model": MODEL_NAME,
        "prompt": full_prompt,
        "stream": False
    }
    
    try:
        start_time = time.time()
        response = requests.post(SLM_URL, json=payload)
        end_time = time.time()
        
        if response.status_code == 200:
            res_json = response.json()
            masked_response = res_json.get("response", "")
            restored_response = pipeline.process_response(masked_response, pipeline_context)
            latency = end_time - start_time

            input_tokens = approximate_token_count(prompt)
            output_tokens = approximate_token_count(restored_response)
            observe_token_usage(input_tokens=input_tokens, output_tokens=output_tokens)
            observe_latency_per_token(latency_seconds=latency, output_tokens=output_tokens)

            return restored_response, latency
        else:
            return f"Server Error: {response.text}", 0.0
            
    except requests.exceptions.ConnectionError:
        return "❌ ERROR: Cannot connect to Ollama (slm-engine). Is the Docker container running?", 0.0

def call_direct_slm(prompt: str) -> str:
    """
    Direct call to SLM without sanitization (for general knowledge).
    """
    response, _ = query_secure_slm(prompt)
    return response

def get_slm_router_decision(text: str) -> str:
    """
    Decides whether to use RAG or Direct SLM.
    Simple keyword-based router for now.
    """
    # In a real system, this would be another SLM call or a classifier.
    # For now, if it asks about "Zyrabit" or specific docs, use RAG.
    keywords = ["zyrabit", "architecture", "security", "slm", "rag"]
    if any(k in text.lower() for k in keywords):
        return "search_rag_database"
    return "direct_SLM_answer"

def execute_rag_pipeline(text: str) -> str:
    """
    Executes the RAG pipeline: Retrieve -> Augment -> Generate.
    Placeholder implementation.
    """
    # 1. Retrieve (Mock)
    context = "Zyrabit SLM is a secure, local AI architecture."
    
    # 2. Augment
    augmented_prompt = f"Context: {context}\n\nQuestion: {text}\n\nAnswer:"
    
    # 3. Generate with security layer enabled
    response, _ = query_secure_slm(augmented_prompt)
    return response

def process_and_ingest_file(file_path: str):
    """
    Mock ingestion function.
    """
    return {"status": "success", "filename": os.path.basename(file_path), "chunks": 10}

# --- EXECUTION ---
if __name__ == "__main__":
    print_header("INITIATING ZERO-TRUST PROTOCOL")

    # CASE 1: HARMLESS QUERY
    query_1 = "What is the capital of France?"
    print(f"\n🗣️  User: {query_1}")
    response, latency = query_secure_slm(query_1)
    print(f"🤖 Zyrabit ({latency:.2f}s): {response.strip()}")

    # CASE 2: DATA LEAK ATTEMPT (Whisper Leak Scenario)
    query_2 = "Draft an email confirming I transferred $50,000.00 USD to account 4532-1234-5678-9012 using my credentials."
    print(f"\n🗣️  User (Risky): {query_2}")
    response, latency = query_secure_slm(query_2)
    
    print_header("SECURE MODEL RESPONSE")
    print(f"🤖 Zyrabit ({latency:.2f}s): {response.strip()}")