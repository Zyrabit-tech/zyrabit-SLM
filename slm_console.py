import os
import sys
import time
from typing import Dict, List

import requests
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


col_chat, col_state = st.columns([3, 2])

with col_state:
    st.subheader("Knowledge State")
    if not st.session_state.ingest_history:
        st.info("No documents ingested in this session.")
    else:
        for item in st.session_state.ingest_history[:8]:
            status_label = "OK" if item["status"] == "success" else "ERROR"
            st.write(
                f"[{status_label}] {item['filename']} | chunks={item['chunks_processed']} | ingest_id={item['ingest_id']}"
            )
            st.caption(item["message"])

with col_chat:
    st.subheader("Secure Chat")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(str(message["content"]))
            if message.get("metadata"):
                _render_route_badge(message["metadata"])
            if message.get("sanitized") and message["role"] == "user":
                with st.expander("Sanitized Preview", expanded=False):
                    st.code(str(message["sanitized"]), language="text")

    prompt = st.chat_input("Ask about your documents or architecture...")
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

