import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_NAME: str = os.getenv("PROJECT_NAME", "zyrabit-slm")
API_V1_STR: str = "/v1"

# Infrastructure URLs
# IMPORTANT: SLM_URL must be the base URL only (e.g. http://host:11434).
# Do NOT include /api/generate or any path — adapters append their own paths.
_raw_slm_url: str = os.getenv("SLM_URL", "http://zyrabit-engine:11434")
SLM_URL: str = _raw_slm_url.rstrip("/").removesuffix("/api/generate")

# DB Configuration (Flexible for Docker/Local)
DB_HOST: str = os.getenv("DB_HOST", "zyrabit-db")
DB_PORT: int = int(os.getenv("DB_PORT", 8000))

# RAG Configuration
RAG_COLLECTION: str = os.getenv("RAG_COLLECTION", "zyrabit_knowledge")
MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen2.5:7b")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "mxbai-embed-large")
# Generation and embeddings may use different local servers.  This is required
# for llama.cpp generation, which does not implement Ollama's /api/embed route.
EMBEDDING_URL: str = os.getenv("EMBEDDING_URL", "http://host.docker.internal:11434").rstrip("/")
NODE_DATA_DIR: str = os.getenv("NODE_DATA_DIR", "/app/db_data/node")
NODE_ENABLE_OCR: bool = os.getenv("NODE_ENABLE_OCR", "false").lower() == "true"
NODE_RETRIEVAL_MODE: str = os.getenv("NODE_RETRIEVAL_MODE", "hybrid").strip().lower()
ENABLE_LEGACY_EXTENSIONS: bool = os.getenv("ENABLE_LEGACY_EXTENSIONS", "false").lower() == "true"

# Security
# Default to local dev origins if not specified. In production, this MUST be set in .env
ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "http://localhost,https://localhost,http://127.0.0.1").split(",")
N8N_SERVICE_TOKEN: str = os.getenv("N8N_SERVICE_TOKEN", "zyrabit-local-token")
DOCS_DIR: str = os.getenv("DOCS_DIR", "./docs")
