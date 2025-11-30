import requests
import json
import re
import time
import os

# --- CONFIGURATION ---
# Use environment variables or default to local settings
SLM_URL = os.getenv("SLM_URL", "http://slm-engine:11434/api/generate")
# Defaulting to phi3 as per setup script, but overridable
MODEL_NAME = os.getenv("MODEL_NAME", "phi3")

def print_header(title: str):
    """Prints a styled header to the console."""
    print(f"\n{'='*60}")
    print(f"🛡️ ZYRABIT SECURITY LAYER: {title}")
    print(f"{'='*60}")

def sanitize_pii(text: str) -> str:
    """
    Scans and redacts Personally Identifiable Information (PII) from the input text.
    
    Current patterns handled:
    - Email addresses
    - Credit Card numbers (simple digit matching)
    - High monetary amounts
    
    Args:
        text (str): The raw input text.
        
    Returns:
        str: The sanitized text with PII replaced by tokens.
    """
    print("   [🔍 Scanning for PII...]")
    
    # Regex rules (In production, this should use a sophisticated NER model)
    
    # Detect Emails
    text = re.sub(r'[\w\.-]+@[\w\.-]+', '[EMAIL_REDACTED]', text)
    
    # Detect Credit Cards (Simulated logic for 13-16 digits)
    text = re.sub(r'\b(?:\d[ -]*?){13,16}\b', '[CREDIT_CARD_REDACTED]', text)
    
    # Detect High Monetary Amounts
    text = re.sub(r'\$\d+(?:,\d{3})*(?:\.\d{2})?', '[AMOUNT_REDACTED]', text)
    
    return text

def query_secure_slm(prompt: str) -> tuple[str, float]:
    """
    Sends a sanitized prompt to the local SLM and returns the response and latency.
    
    Args:
        prompt (str): The user's input prompt.
        
    Returns:
        tuple[str, float]: A tuple containing the (response_text, latency_in_seconds).
    """
    # PHASE A: SANITIZATION (Sidecar Pattern)
    sanitized_prompt = sanitize_pii(prompt)
    
    if sanitized_prompt != prompt:
        print(f"   ⚠️  THREAT DETECTED. DATA REDACTED.")
        print(f"   ORIGINAL: {prompt}")
        print(f"   SENT:     {sanitized_prompt}")
    else:
        print("   ✅ Input clean. Forwarding to core.")

    # PHASE B: LOCAL INFERENCE (Air-Gapped)
    payload = {
        "model": MODEL_NAME,
        "prompt": sanitized_prompt + " (Answer concisely in English)",
        "stream": False
    }
    
    try:
        start_time = time.time()
        response = requests.post(SLM_URL, json=payload)
        end_time = time.time()
        
        if response.status_code == 200:
            res_json = response.json()
            return res_json.get('response', ''), end_time - start_time
        else:
            return f"Server Error: {response.text}", 0.0
            
    except requests.exceptions.ConnectionError:
        return "❌ ERROR: Cannot connect to Ollama (slm-engine). Is the Docker container running?", 0.0

def call_direct_slm(prompt: str) -> str:
    """
    Direct call to SLM without sanitization (for general knowledge).
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(SLM_URL, json=payload)
        if response.status_code == 200:
            return response.json().get('response', '')
        return f"Error: {response.status_code}"
    except Exception as e:
        return f"Connection Error: {str(e)}"

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
    
    # 3. Generate
    return call_direct_slm(augmented_prompt)

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