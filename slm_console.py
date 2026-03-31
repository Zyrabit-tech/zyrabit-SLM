import os
import sys
import time
from typing import Dict, List

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import streamlit as st

# --- PATH CONFIGURATION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(current_dir, "zyrabit-brain-api", "api-rag")
sys.path.append(backend_path)

try:
    from app.security import sanitize_pii
except ImportError as exc:
    st.error(f"Critical Import Error: {exc}")

    def sanitize_pii(text):
        return text, False


API_URL = os.getenv("API_URL", "https://localhost/v1/chat")
HEALTH_URL = os.getenv("HEALTH_URL", "https://localhost/health")
INGEST_URL = os.getenv("INGEST_URL", "https://localhost/v1/ingest")
VERIFY_TLS = os.getenv("VERIFY_TLS", "false").lower() == "true"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "90"))


def _parse_api_error(response: requests.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            if "detail" in payload:
                return str(payload["detail"])
            if "error" in payload:
                return str(payload["error"])
    except ValueError:
        pass
    return "Error inesperado del servidor."


def _ingest_uploaded_file(uploaded_file) -> Dict[str, str]:
    file_bytes = uploaded_file.getvalue()
    mime_type = uploaded_file.type or "application/octet-stream"
    files = {"file": (uploaded_file.name, file_bytes, mime_type)}
    response = requests.post(
        INGEST_URL,
        files=files,
        verify=VERIFY_TLS,
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code == 200:
        data = response.json()
        return {
            "status": "success",
            "filename": data.get("filename", uploaded_file.name),
            "chunks_processed": str(data.get("chunks_processed", 0)),
            "ingest_id": data.get("ingest_id", "n/a"),
            "message": data.get("message", "Documento procesado."),
        }

    return {
        "status": "error",
        "filename": uploaded_file.name,
        "chunks_processed": "-",
        "ingest_id": "n/a",
        "message": f"{response.status_code}: {_parse_api_error(response)}",
    }


def _render_route_badge(metadata: Dict[str, object]):
    route = str(metadata.get("route_decision", "unknown"))
    rag_hits = metadata.get("rag_hits", 0)
    latency_ms = metadata.get("latency_ms", 0)
    st.caption(f"Route: {route} | rag_hits: {rag_hits} | latency_ms: {latency_ms}")


st.set_page_config(
    page_title="Zyrabit SLM Enterprise Console",
    layout="wide",
    page_icon="🛡️",
)

st.title("Zyrabit SLM Enterprise Layer")
st.caption("Secure Chat + Document Upload + RAG")

if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, object]] = []

if "ingest_history" not in st.session_state:
    st.session_state.ingest_history: List[Dict[str, str]] = []

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0


with st.sidebar:
    st.header("Node Status")
    try:
        health_response = requests.get(HEALTH_URL, timeout=3, verify=VERIFY_TLS)
        if health_response.status_code == 200:
            st.success("Core API: ONLINE")
        else:
            st.warning(f"Core API: DEGRADED ({health_response.status_code})")
    except requests.exceptions.RequestException:
        st.error("Core API: OFFLINE")

    st.markdown("---")
    st.subheader("Document Ingestion")
    uploaded_files = st.file_uploader(
        "Upload files (.pdf, .txt, .md)",
        type=["pdf", "txt", "md"],
        accept_multiple_files=True,
        key=str(st.session_state.uploader_key)
    )

    ingest_clicked = st.button(
        "Ingest Documents",
        type="primary",
        disabled=not uploaded_files,
    )

    if ingest_clicked and uploaded_files:
        progress = st.progress(0)
        for index, uploaded_file in enumerate(uploaded_files):
            try:
                result = _ingest_uploaded_file(uploaded_file)
            except requests.exceptions.RequestException as exc:
                result = {
                    "status": "error",
                    "filename": uploaded_file.name,
                    "chunks_processed": "-",
                    "ingest_id": "n/a",
                    "message": f"Connection error: {exc}",
                }

            st.session_state.ingest_history.insert(0, result)
            progress.progress((index + 1) / len(uploaded_files))
        progress.empty()
        st.success("Ingestion completed.")
        st.session_state.uploader_key += 1
        st.rerun()

    st.markdown("---")
    st.subheader("Knowledge State")

    # Show session ingestion results first
    if st.session_state.ingest_history:
        for item in st.session_state.ingest_history[:8]:
            status_label = "✅" if item["status"] == "success" else "❌"
            st.write(
                f"{status_label} **{item['filename']}** | chunks={item['chunks_processed']}"
            )
            st.caption(item["message"])
        st.markdown("---")

    # Fetch persisted documents from vault via API
    DOCUMENTS_URL = os.getenv("DOCUMENTS_URL", "https://localhost/v1/documents")
    try:
        docs_resp = requests.get(DOCUMENTS_URL, timeout=3, verify=VERIFY_TLS)
        if docs_resp.status_code == 200:
            docs_data = docs_resp.json()
            vault_docs = docs_data.get("documents", [])
            total = docs_data.get("total", len(vault_docs))
            if vault_docs:
                st.metric("Documents in Vault", total)
                for doc in vault_docs[:10]:
                    size_kb = round(doc.get("size_bytes", 0) / 1024, 1)
                    st.caption(f"📄 {doc['filename']} ({size_kb} KB)")
            else:
                st.info("No documents in the knowledge vault yet.")
        else:
            st.info("No documents ingested in this session.")
    except requests.exceptions.RequestException:
        if not st.session_state.ingest_history:
            st.info("No documents ingested in this session.")


tab_chat, tab_support = st.tabs(["💬 Chat Principal", "🛠️ Soporte de Instalación"])

with tab_chat:
    st.subheader("Secure Chat")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(str(message["content"]))
            if message.get("metadata"):
                _render_route_badge(message["metadata"])
            if message.get("sanitized") and message["role"] == "user":
                with st.expander("Sanitized Preview", expanded=False):
                    st.code(str(message["sanitized"]), language="text")

    prompt = st.chat_input("Ask about your documents or architecture...", key="main_chat")
    if prompt:
        sanitized_text, was_sanitized = sanitize_pii(prompt)
        user_message = {"role": "user", "content": prompt}
        if was_sanitized:
            user_message["sanitized"] = sanitized_text
        st.session_state.messages.append(user_message)

        with st.chat_message("user"):
            st.markdown(prompt)
            if was_sanitized:
                with st.expander("Sanitized Preview", expanded=False):
                    st.code(sanitized_text, language="text")

        payload = {"text": prompt}
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    start_time = time.time()
                    response = requests.post(
                        API_URL,
                        json=payload,
                        verify=VERIFY_TLS,
                        timeout=REQUEST_TIMEOUT,
                    )
                    end_time = time.time()

                    if response.status_code == 200:
                        data = response.json()
                        answer = data.get("response", "No response content.")
                        metadata = data.get("metadata", {})
                        if "latency_ms" not in metadata:
                            metadata["latency_ms"] = round((end_time - start_time) * 1000, 2)

                        st.markdown(answer)
                        if metadata:
                            _render_route_badge(metadata)

                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": answer,
                                "metadata": metadata,
                            }
                        )
                    else:
                        error_msg = _parse_api_error(response)
                        st.error(f"API Error {response.status_code}: {error_msg}")
                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": f"API Error {response.status_code}: {error_msg}",
                            }
                        )
                except requests.exceptions.RequestException as exc:
                    st.error(f"Connection error: {exc}")
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": f"Connection error: {exc}",
                        }
                    )

with tab_support:
    st.subheader("Asistente de Despliegue MCP")
    st.info("Este agente puede invocar herramientas reales en tu servidor (via el servicio `mcp-server`) para diagnosticar el estado del contenedor Docker.")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🚀 Diagnóstico Rápido", type="primary", use_container_width=True):
            with st.spinner("Analizando contenedores Docker..."):
                try:
                    res = requests.get("http://localhost:8001/diagnose", timeout=15)
                    if res.status_code == 200:
                        diag_data = res.json()
                        st.session_state.support_messages = st.session_state.get("support_messages", [])
                        sys_prompt = {"role": "system", "content": "Eres el experto en despliegue de Zyrabit. Usa los logs del sistema para guiar al usuario. Si detectas que falta la GPU, sugiere el modo 'Ollama Nativo'."}
                        if sys_prompt not in st.session_state.support_messages:
                            st.session_state.support_messages.insert(0, sys_prompt)
                        
                        diag_msg = f"**Diagnóstico detectado:**\n```\n{diag_data.get('status', '')}\n```\n\n**Sugerencia:** {diag_data.get('suggested_fix', '')}"
                        st.session_state.support_messages.append({"role": "assistant", "content": diag_msg})
                        st.success("Diagnóstico completado")
                        st.rerun()
                    else:
                        st.error(f"Error MCP Server: {res.status_code}")
                except Exception as e:
                    st.error(f"Falla de conexión al MCP: {e}. ¿Está corriendo el mcp-server?")
                    
    with col2:
        st.caption("Usa el diagnóstico rápido para consultar los contenedores actualmente en ejecución en la máquina Host, gracias a volume binding de Docker.")

    if "support_messages" not in st.session_state:
        st.session_state.support_messages = []
        
    for msg in st.session_state.support_messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    support_prompt = st.chat_input("Pregunta algo al técnico de Zyrabit...", key="support_chat")
    if support_prompt:
        # Note: here we simulate interaction using the base API or directly adding messages.
        # En una arquitectura completa la consulta pasaría de nuevo a Ollama inyectando los tools.
        st.session_state.support_messages.append({"role": "user", "content": support_prompt})
        with st.chat_message("user"):
            st.markdown(support_prompt)
            
        with st.chat_message("assistant"):
            with st.spinner("Analizando log y guía..."):
                # Se podría pasar a la API normal adjuntando el system prompt y docs
                fast_payload = {"text": f"SYSTEM: Eres el experto en despliegue de Zyrabit. Usa los logs del sistema para guiar al usuario. Si detectas que falta la GPU, sugiere el modo 'Ollama Nativo'. USER: {support_prompt}"}
                try:
                    s_res = requests.post(API_URL, json=fast_payload, verify=VERIFY_TLS, timeout=REQUEST_TIMEOUT)
                    if s_res.status_code == 200:
                        s_ans = s_res.json().get("response", "")
                        st.markdown(s_ans)
                        st.session_state.support_messages.append({"role": "assistant", "content": s_ans})
                except Exception as x:
                    st.error("Error al consultar asistencia")


