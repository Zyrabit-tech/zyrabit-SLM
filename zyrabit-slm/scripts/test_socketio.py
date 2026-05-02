import socketio
import uuid
import time

# Configuration
SOCKET_URL = "http://127.0.0.1:8080"
msg_id = str(uuid.uuid4())

# Initialize Client
sio = socketio.Client()

@sio.event
def connect():
    print("✅ Connected to Zyrabit Socket.io Gateway!")

@sio.event
def disconnect():
    print("🛑 Disconnected from server")

@sio.on("chat_response")
def on_message(data):
    print("\n📩 Received Chat Response via Socket.io:")
    print(f"📄 Response: {data.get('response')[:100]}...")
    print(f"📊 Metadata: {data.get('metadata')}")
    
    # Check for idempotency test success
    if "latency_ms" in data.get("metadata", {}):
        print("\n🔥 WebSocket Bridge Verified: Success!")
    
    sio.disconnect()

def main():
    try:
        print(f"🚀 Connecting to {SOCKET_URL}...")
        sio.connect(SOCKET_URL, transports=['websocket', 'polling'])
        
        test_payload = {
            "text": "What is the status of the Zyrabit infrastructure?",
            "client_msg_id": msg_id
        }
        
        print(f"📤 Sending message (msg_id: {msg_id})...")
        sio.emit("chat_message", test_payload)
        
        # Wait for response (timeout 10s)
        sio.wait()
        
    except Exception as e:
        print(f"❌ Socket.io Error: {e}")
        print("\nTip: If you don't have the library, run: pip install \"python-socketio[client]\"")

if __name__ == "__main__":
    main()
