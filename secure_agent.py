import requests
import json
import re
import time

# --- CONFIGURACIÓN ---
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"

def print_header(title):
    print(f"\n{'='*60}")
    print(f"🛡️ ZYRABIT SECURITY LAYER: {title}")
    print(f"{'='*60}")

# 1. EL "SIDECAR" DE SEGURIDAD (PII STRIPPER)
# Esto simula el firewall semántico que evita fugas de datos
def sanitize_input(text):
    print("   [🔍 Scanning for PII...]")
    
    # Reglas simples de Regex (En prod esto sería un modelo NER local)
    # Detectar Emails
    text = re.sub(r'[\w\.-]+@[\w\.-]+', '[EMAIL_REDACTED]', text)
    # Detectar Tarjetas de Crédito (Simuladas con 16 dígitos)
    text = re.sub(r'\b(?:\d[ -]*?){13,16}\b', '[CREDIT_CARD_REDACTED]', text)
    # Detectar Montos en Dólares altos
    text = re.sub(r'\$\d+(?:,\d{3})*(?:\.\d{2})?', '[AMOUNT_REDACTED]', text)
    
    return text

# 2. EL CLIENTE SOBERANO
def ask_secure_llm(prompt):
    # FASE A: SANITIZACIÓN
    clean_prompt = sanitize_input(prompt)
    
    if clean_prompt != prompt:
        print(f"   ⚠️  AMENAZA DETECTADA. DATOS LIMPIADOS.")
        print(f"   ORIGINAL: {prompt}")
        print(f"   ENVIADO:  {clean_prompt}")
    else:
        print("   ✅ Input limpio. Enviando al núcleo.")

    # FASE B: INFERENCIA LOCAL (AIR GAPPED)
    payload = {
        "model": MODEL,
        "prompt": clean_prompt + " (Responde brevemente en español)",
        "stream": False
    }
    
    try:
        start = time.time()
        response = requests.post(OLLAMA_URL, json=payload)
        end = time.time()
        
        if response.status_code == 200:
            res_json = response.json()
            return res_json['response'], end - start
        else:
            return f"Error: {response.text}", 0
            
    except requests.exceptions.ConnectionError:
        return "❌ ERROR: No puedo conectar con Ollama. ¿Está corriendo el Docker?", 0

# --- EJECUCIÓN ---
if __name__ == "__main__":
    print_header("INICIANDO PROTOCOLO ZERO-TRUST")

    # CASO 1: PREGUNTA INOCENTE
    p1 = "¿Cuál es la capital de Francia?"
    print(f"\n🗣️  Usuario: {p1}")
    res, t = ask_secure_llm(p1)
    print(f"🤖 Zyrabit ({t:.2f}s): {res.strip()}")

    # CASO 2: INTENTO DE FUGA DE DATOS (WHISPER LEAK SCENARIO)
    p2 = "Redacta un correo confirmando que transferí $50,000.00 USD a la cuenta de ventas@competencia.com usando mi tarjeta 4532-1234-5678-9012."
    print(f"\n🗣️  Usuario (Riesgoso): {p2}")
    res, t = ask_secure_llm(p2)
    
    print_header("RESPUESTA SEGURA DEL MODELO")
    print(f"🤖 Zyrabit ({t:.2f}s): {res.strip()}")
