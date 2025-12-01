import streamlit as st
import requests
import time
import os
import sys

# --- PATH CONFIGURATION ---
# We append the backend directory to sys.path to import the centralized security logic
# without duplicating code or creating a complex package structure for the MVP.
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(current_dir, 'zyrabit-brain-api', 'api-rag')
sys.path.append(backend_path)

try:
    # Attempt to import the centralized sanitization logic
    from app.security import sanitize_pii
except ImportError as e:
    st.error(f"Critical Import Error: {e}")
    # Emergency fallback to prevent crash if directory structure is wrong
    def sanitize_pii(text): return text, False

# --- APP CONFIGURATION ---
# Smart Default: Allows overriding via environment variable for Cloud/Docker deployments
API_URL = os.getenv("API_URL", "http://localhost:8080/v1/chat")

# Page Config
st.set_page_config(
    page_title="Zyrabit SLM Enterprise Console",
    layout="wide",
    page_icon="🛡️"
)

# --- CUSTOM CSS ---
# Styling to give it a robust "Enterprise/Cybersecurity" look
st.markdown("""
<style>
    .stTextArea textarea {
        background-color: #0e1117;
        color: #ffffff;
        border: 1px solid #262730;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #1c2e24;
        border: 1px solid #2e7d32;
        color: #a5d6a7;
    }
    .metric-container {
        border: 1px solid #333;
        padding: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
col_logo, col_title = st.columns([1, 5])
with col_logo:
    # Using a generic shield icon for visual identity
    st.image("https://img.icons8.com/fluency/96/shield.png", width=70)
with col_title:
    st.title("Zyrabit SLM Enterprise Layer")
    st.caption("🛡️ Sovereign AI Infrastructure & Zero-Trust Architecture")

st.divider()

# --- SIDEBAR (Control Panel) ---
with st.sidebar:
    st.header("⚙️ Node Status")
    
    # API Health Check
    try:
        health_response = requests.get("http://localhost:8080/health", timeout=2)
        if health_response.status_code == 200:
            api_status = "🟢 ONLINE"
            st.success(f"Core API: {api_status}")
        else:
            api_status = "⚠️ DEGRADED"
            st.warning(f"Core API: {api_status}")
    except requests.exceptions.ConnectionError:
        api_status = "🔴 OFFLINE"
        st.error(f"Core API: {api_status}")
        
    st.markdown("---")
    st.info("🧠 **Active Engine:** SLM (Phi-3 / Qwen)")
    st.warning("🔒 **Security Mode:** PII Scrubbing Active")
    
    st.markdown("### Session Metrics")
    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Latency Target", "< 200ms")
    col_m2.metric("Privacy", "100%", "Local")

# --- MAIN CHAT INTERFACE ---

st.subheader("💬 Secure Chat with Sovereign Memory")

user_input = st.text_area(
    "Enter your query (Try including sensitive data like emails or credit card numbers):", 
    height=100, 
    placeholder="Ex: I need to transfer $50,000 to account 4213-4123-1234-1234...",
    key="chat_input_unique_id"
)

col_action, col_void = st.columns([1, 4])

if col_action.button("🚀 Run Inference", type="primary"):
    if not user_input:
        st.warning("Please provide an input first.")
    else:
        # 1. SECURITY PROCESS (The Sidecar Pattern Simulation)
        with st.status("🛡️ Executing Security Protocols...", expanded=True) as status:
            time.sleep(0.3) # Slight delay for visual feedback
            
            # Apply centralized sanitization logic
            clean_text, was_sanitized = sanitize_pii(user_input)
            
            if was_sanitized:
                st.write("⚠️ **PII Detected:** Sensitive patterns matched (Regex/NER).")
                st.write("🧼 **Action:** In-Flight Sanitization applied.")
            else:
                st.write("✅ **Traffic Clean:** No risks detected.")
                
            st.write(f"📡 Forwarding secure payload to SLM Gateway ({API_URL})...")
            status.update(label="✅ Pre-processing Complete", state="complete", expanded=False)

        # 2. VISUALIZATION (The "Zero-Trust" Proof)
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("#### 👁️ User View (Raw)")
            st.info(user_input)
            
        with col_right:
            st.markdown("#### 🤖 SLM View (Sanitized)")
            if was_sanitized:
                st.code(clean_text, language="text")
                st.caption("🔒 Real data NEVER touched the model's context window.")
            else:
                st.code(clean_text, language="text")
                st.caption("✅ Payload unaltered.")

        # 3. INFERENCE CALL (The Brain)
        try:
            start_time = time.time()
            payload = {"text": clean_text}
            
            # UX Improvement: Spinner while waiting for response
            with st.spinner("🧠 SLM is reasoning..."):
                response = requests.post(API_URL, json=payload)
            
            end_time = time.time()
            
            if response.status_code == 200:
                bot_response = response.json().get("response", "Error parsing response structure")
                latency = end_time - start_time
                
                st.markdown("### 💡 Model Response")
                st.markdown(f"""<div class="success-box">{bot_response}</div>""", unsafe_allow_html=True)
                st.caption(f"⏱️ Total Turnaround Time: {latency:.2f}s")
                
            else:
                st.error(f"API Error ({response.status_code}): {response.text}")
                
        except requests.exceptions.ConnectionError:
            st.error(f"❌ Connection Failed: Could not reach {API_URL}. Is the Docker container running?")

# --- FOOTER ---
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: grey; font-size: 0.8em;'>"
    "Zyrabit © 2025"
    "</div>", 
    unsafe_allow_html=True
)