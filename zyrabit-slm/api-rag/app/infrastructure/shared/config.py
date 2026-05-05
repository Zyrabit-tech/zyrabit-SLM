import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_NAME: str = os.getenv("PROJECT_NAME", "zyrabit-slm")
API_V1_STR: str = "/v1"

# Infrastructure URLs
SLM_URL: str = os.getenv("SLM_URL", "http://host.docker.internal:11434")

# DB Configuration (Flexible for Docker/Local)
DB_HOST: str = os.getenv("DB_HOST", "zyrabit-db")
DB_PORT: int = int(os.getenv("DB_PORT", 8000))

# RAG Configuration
RAG_COLLECTION: str = os.getenv("RAG_COLLECTION", "zyrabit_knowledge")
MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen2.5:7b")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "mxbai-embed-large")

# Security
N8N_SERVICE_TOKEN: str = os.getenv("N8N_SERVICE_TOKEN", "zyrabit-local-token")
DOCS_DIR: str = os.getenv("DOCS_DIR", "./docs")
