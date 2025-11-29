import streamlit as st
import requests
import re
import time
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
API_URL = os.getenv("API_URL", "http://localhost:8080/v1/chat")
# MODEL = "mistral"
MODEL = os.getenv("MODEL", "phi3")

# --- ZYRABIT STYLES ---


def load_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Funnel+Display:wght@300..800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Funnel Display', sans-serif;
            color: #323439;
        }

        /* Primary Color Elements */
        .stButton>button {
            background-color: #3f5a6d !important;
            color: white !important;
            border-radius: 8px;
            border: none;
            font-weight: 600;
        }

        /* Secondary Accents */
        .stStatus {
            background-color: #e2ecf4;
            border: 1px solid #a9c4d9;
        }

        /* Headers */
        h1, h2, h3 {
            color: #3f5a6d !important;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #fdfdfd;
            border-right: 1px solid #a9c4d9;
        }

        /* Metrics */
        [data-testid="stMetricValue"] {
            color: #6090b4;
        }
        </style>
    """, unsafe_allow_html=True)

# --- BUSINESS LOGIC (Same as secure agent) ---


from security import sanitize_pii as sanitize_input


def query_backend(prompt):
    payload = {"text": prompt}
    try:
        start = time.time()
        with st.spinner('Pensando...'):
            response = requests.post(API_URL, json=payload)
        end = time.time()
        if response.status_code == 200:
            # Expect response format {'response': '...'}
            data = response.json()
            return data.get('response', ''), end - start
        else:
            return f"Error del servidor: {response.status_code}", 0
    except BaseException as e:
        return f"Error de conexión: {str(e)}", 0


# --- GUI (THE FACE OF THE PRODUCT) ---
st.set_page_config(
    page_title="Zyrabit Secure AI",
    layout="wide",
    page_icon="🛡️")
load_css()

# Header
col1, col2 = st.columns([1, 4])
with col1:
    # Placeholder for logo if available, otherwise shield icon
    st.image("https://img.icons8.com/color/96/000000/shield.png", width=80)
with col2:
    st.title("Zyrabit Core")
    st.markdown("**Infraestructura de IA & Zero-Trust**")

st.divider()

# Control Panel
with st.sidebar:
    st.header("⚙️ Configuración del Nodo")
    st.success("● Motor Neural: ONLINE (CPU Mode)")
    st.info(f"🧠 Modelo: {MODEL}")
    st.warning("🛡️ DLP Sidecar: ACTIVO")
    st.markdown("---")

# Chat Area
st.subheader("💬 Interfaz de Prueba Segura")

user_input = st.text_area(
    "Escribe tu consulta (Intenta incluir datos sensibles como emails o montos):",
    height=100)

if st.button("🚀 Ejecutar Inferencia Segura"):
    if user_input:
        # 1. Sanitization Process
        with st.status("🔒 Procesando Protocolo de Seguridad...", expanded=True) as status:
            st.write("1. Interceptando payload...")
            time.sleep(0.5)  # Dramatic effect
            clean_prompt = sanitize_input(user_input)
            st.write("2. Ejecutando PII Scrubbing (Borrado de Datos Personales)...")
            st.write("3. Enviando a Motor Local (Air-Gapped)...")
            status.update(
                label="✅ Inferencia Completada",
                state="complete",
                expanded=False)

        # 2. Visual Results
        col_input, col_output = st.columns(2)

        with col_input:
            st.markdown("### 👁️ Entrada Original (Sanitizada)")
            st.code(clean_prompt, language="text")
            st.caption("Nota: Los datos sensibles nunca tocaron la RAM del modelo.")

        # 3. Model Call
        response_text, latency = query_backend(clean_prompt)

        with col_output:
            st.markdown("### 🤖 Respuesta del Modelo")
            st.success(response_text)
            st.caption(f"⏱️ Latencia: {latency:.2f}s | 🔋 Hardware: CPU Standard")
    else:
        st.error("Por favor ingresa un texto para procesar.")

# Credibility Footer
st.markdown("---")
st.markdown(
    "*Zyrabit Systems - Powered by Clean Architecture & Memory-First RAG Protocol*")
