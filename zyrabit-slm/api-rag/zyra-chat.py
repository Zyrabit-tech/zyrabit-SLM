#!/usr/bin/env python3
import requests
import sys

API_URL = "http://localhost:8082/v1/chat"

def chat(query):
    payload = {
        "text": query,
        "history": []
    }
    
    try:
        print("\n[ZYRA]: Procesando consulta...\n")
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        
        print("--- RESPUESTA ---")
        print(data.get("response"))
        print("-----------------")
        
        meta = data.get("metadata", {})
        print(f"\n[META] Latencia: {meta.get('latency_ms')}ms | Modo: {meta.get('decision')} | Hits RAG: {meta.get('rag_hits')}")
        
    except Exception as e:
        print(f"❌ Error conectando con Zyrabit API: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 zyra-chat.py \"Tu pregunta aquí\"")
    else:
        chat(" ".join(sys.argv[1:]))
