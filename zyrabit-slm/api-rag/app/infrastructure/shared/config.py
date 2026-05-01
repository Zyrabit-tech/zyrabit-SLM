import os
from typing import Optional

# --- Zyrabit SLM Configuration ---
# Source of Truth: Environment Variables

SLM_URL: str = os.getenv("SLM_URL", "http://host.docker.internal:11434")
DB_URL: str = os.getenv("DB_URL", "http://zyrabit-db:8000")
MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen2.5:7b")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "mxbai-embed-large")

# RAG Configuration
RAG_COLLECTION: str = os.getenv("RAG_COLLECTION", "zyrabit_knowledge")
DOCS_DIR: str = os.getenv("DOCS_DIR", "./document_source")

# Security Configuration
GATEKEEPER_STRICT_MODE: bool = os.getenv("GATEKEEPER_STRICT_MODE", "true").lower() == "true"

# API Configuration
API_V1_STR: str = "/v1"
PROJECT_NAME: str = "Zyrabit SLM"

def get_slm_generate_url() -> str:
    return f"{SLM_URL.rstrip('/')}/api/generate"

def get_slm_embeddings_url() -> str:
    return f"{SLM_URL.rstrip('/')}/api/embeddings"
