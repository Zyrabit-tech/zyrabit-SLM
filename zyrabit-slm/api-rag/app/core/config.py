import os
from urllib.parse import urlparse

SLM_URL = os.getenv("SLM_URL", "http://host.docker.internal:11434")
DB_URL = os.getenv("DB_URL", "http://zyrabit-db:8000")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:7b")
COLLECTION_NAME = os.getenv("RAG_COLLECTION", "zyrabit_knowledge")
INGEST_DIR = os.getenv("DOCS_DIR", "./document_source")
