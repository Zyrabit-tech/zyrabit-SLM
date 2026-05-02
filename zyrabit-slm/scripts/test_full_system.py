import urllib.request
import json
import uuid
import time
import ssl

# Configuration
SOCKET_URL = "http://127.0.0.1:8080"
API_URL = f"{SOCKET_URL}/v1/chat"
HEADERS = {"Content-Type": "application/json"}

def run_test(name, payload):
    print(f"🧪 Testing: {name}")
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(API_URL, data=data, headers=HEADERS, method='POST')
    
    try:
        start = time.time()
        print(f"📡 Sending request to {API_URL}...")
        with urllib.request.urlopen(req, timeout=45) as f:
            res = json.loads(f.read().decode('utf-8'))
            latency = time.time() - start
            print(f"✅ Success ({latency:.2f}s)")
            return res
    except Exception as e:
        print(f"❌ Failed: {e}")
        return None

def main():
    print("🚀 STARTING ZYRABIT SYSTEM VALIDATION\n")

    # 1. Test Gatekeeper (Rejection)
    run_test("Gatekeeper Rejection (Out of Scope)", {
        "text": "How do I make a pizza?",
        "client_msg_id": str(uuid.uuid4())
    })

    print("\n" + "-"*40 + "\n")

    # 2. Test PII Masking
    res_pii = run_test("PII Masking (Email & IP)", {
        "text": "My email is admin@zyrabit.ai and my server is 192.168.1.1. How is Zyrabit?",
        "client_msg_id": str(uuid.uuid4())
    })
    if res_pii:
        print(f"🔍 PII Detected in Metadata: {res_pii['metadata'].get('pii_detected')}")
        # Note: We expect the response NOT to contain the plain email if the LLM followed the masked prompt
    
    print("\n" + "-"*40 + "\n")

    # 3. Test RAG Flow (Context Retrieval)
    res_rag = run_test("RAG Flow (Zyrabit Context)", {
        "text": "What is the purpose of Zyrabit SLM?",
        "client_msg_id": str(uuid.uuid4())
    })
    if res_rag:
        print(f"🔍 Decision: {res_rag['metadata'].get('decision')}")
        print(f"📚 Sources: {res_rag['metadata'].get('sources')}")

    print("\n" + "-"*40 + "\n")

    # 4. Final Idempotency Check
    m_id = str(uuid.uuid4())
    p = {"text": "Tell me about Docker hardening.", "client_msg_id": m_id}
    run_test("Idempotency - Part 1 (Original)", p)
    time.sleep(1)
    run_test("Idempotency - Part 2 (Cache Hit)", p)

if __name__ == "__main__":
    main()
