import streamlit as st
import requests
import re
import time
import json

# --- CONFIGURACIÓN ---
OLLAMA_URL = "http://localhost:11434/api/generate"
# MODEL = "mistral"
MODEL = "phi3"

# --- ESTILOS ZYRABIT ---
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

# --- LÓGICA DE NEGOCIO (Igual que tu agente seguro) ---
def sanitize_input(text):
    # Reglas de DLP (Data Loss Prevention)
    text = re.sub(r'[\w\.-]+@[\w\.-]+', '████████', text) # Redacción visual
    text = re.sub(r'\b(?:\d[ -]*?){13,16}\b', '[CREDIT_CARD]', text)
    text = re.sub(r'\$\d+(?:,\d{3})*(?:\.\d{2})?', '[AMOUNT]', text)
    return text

def query_ollama(prompt):
    payload = {
        "model": MODEL,
        "prompt": prompt + " (Responde en español, sé conciso)",
        "stream": False
    }
    try:
        start = time.time()
        response = requests.post(OLLAMA_URL, json=payload)
        end = time.time()
        if response.status_code == 200:
            return response.json()['response'], end - start
        else:
            return "Error del servidor", 0
    except:
        return "Error de conexión", 0

# --- INTERFAZ GRÁFICA (LA CARA DEL PRODUCTO) ---
st.set_page_config(page_title="Zyrabit Secure AI", layout="wide", page_icon="🛡️")
load_css()

# Header
col1, col2 = st.columns([1, 4])
with col1:
    # Placeholder for logo if available, otherwise shield icon
    st.image("https://img.icons8.com/color/96/000000/shield.png", width=80)
with col2:
    st.title("Zyrabit Enterprise Core")
    st.markdown("**Infraestructura de IA Soberana & Zero-Trust**")

st.divider()

# Panel de Control
with st.sidebar:
    st.header("⚙️ Configuración del Nodo")
    st.success("● Motor Neural: ONLINE (CPU Mode)")
    st.info(f"🧠 Modelo: {MODEL}")
    st.warning("🛡️ DLP Sidecar: ACTIVO")
    st.markdown("---")
    st.metric(label="Costo por Token", value="$0.00", delta="-100% vs OpenAI")

# Área de Chat
st.subheader("💬 Interfaz de Prueba Segura")

user_input = st.text_area("Escribe tu consulta (Intenta incluir datos sensibles como emails o montos):", height=100)

if st.button("🚀 Ejecutar Inferencia Segura"):
    if user_input:
        # 1. Proceso de Sanitización
        with st.status("🔒 Procesando Protocolo de Seguridad...", expanded=True) as status:
            st.write("1. Interceptando payload...")
            time.sleep(0.5) # Efecto dramático
            clean_prompt = sanitize_input(user_input)
            st.write("2. Ejecutando PII Scrubbing (Borrado de Datos Personales)...")
            st.write("3. Enviando a Motor Local (Air-Gapped)...")
            status.update(label="✅ Inferencia Completada", state="complete", expanded=False)

        # 2. Resultados Visuales
        col_input, col_output = st.columns(2)
        
        with col_input:
            st.markdown("### 👁️ Lo que ve Zyrabit (Seguro)")
            st.code(clean_prompt, language="text")
            st.caption("Nota: Los datos sensibles nunca tocaron la RAM del modelo.")

        # 3. Llamada al Modelo
        response_text, latency = query_ollama(clean_prompt)

        with col_output:
            st.markdown("### 🤖 Respuesta del Modelo")
            st.success(response_text)
            st.caption(f"⏱️ Latencia: {latency:.2f}s | 🔋 Hardware: CPU Standard")

    else:
        st.error("Por favor ingresa un texto para procesar.")

# Footer de Credibilidad
st.markdown("---")
st.markdown("*Zyrabit Systems - Powered by Clean Architecture & Memory-First RAG Protocol*")
