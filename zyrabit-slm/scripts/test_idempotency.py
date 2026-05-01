import urllib.request
import urllib.parse
import uuid
import time
import json

# Configuration - Bypassing Traefik/SSL for direct local testing on port 8080
API_URL = "http://localhost:8080/v1/chat" 
HEADERS = {"Content-Type": "application/json"}

def test_idempotency():
    msg_id = str(uuid.uuid4())
    payload = {
        "text": "What is the capital of France?",
        "client_msg_id": msg_id
    }
    data = json.dumps(payload).encode('utf-8')

    print(f"🚀 Sending FIRST request (msg_id: {msg_id})...")
    start_time = time.time()
    
    try:
        # Request 1
        req1 = urllib.request.Request(API_URL, data=data, headers=HEADERS, method='POST')
        with urllib.request.urlopen(req1) as f:
            res1 = json.loads(f.read().decode('utf-8'))
            duration1 = time.time() - start_time
            print(f"✅ Response 1 received in {duration1:.2f}s")
            print(f"📄 Answer: {res1.get('response')[:50]}...")

        print("\n" + "-"*50 + "\n")

        # Request 2
        print(f"🚀 Sending SECOND request with SAME msg_id...")
        start_time = time.time()
        req2 = urllib.request.Request(API_URL, data=data, headers=HEADERS, method='POST')
        with urllib.request.urlopen(req2) as f:
            res2 = json.loads(f.read().decode('utf-8'))
            duration2 = time.time() - start_time
            
            print(f"✅ Response 2 received in {duration2:.2f}s")
            
            if duration2 < duration1 * 0.2: # Expecting at least 5x faster
                print("\n🔥 SUCCESS: Idempotency cache hit! The second response was instant.")
            else:
                print(f"\n⚠️ WARNING: Second request took {duration2:.2f}s. Check if Ollama cached it instead of Zyrabit.")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("Tip: Make sure zyrabit-api is running on port 8080.")

if __name__ == "__main__":
    test_idempotency()
