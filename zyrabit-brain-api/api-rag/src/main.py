from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from prometheus_fastapi_instrumentator import Instrumentator
import os

# Inicializa la app FastAPI
app = FastAPI(title="Zyrabit Brain API")

# Añade métricas de Prometheus
Instrumentator().instrument(app).expose(app)

# Modelo para las peticiones de consulta
class QueryRequest(BaseModel):
    question: str

# Configura las conexiones usando variables de entorno
LLM_URL = os.environ.get("LLM_URL", "http://llm-server:11434")
DB_URL = os.environ.get("DB_URL", "http://vector-db:8000")

# Inicializa el modelo y las embeddings
llm = Ollama(base_url=LLM_URL, model="phi")
embeddings = OllamaEmbeddings(base_url=LLM_URL)

@app.post("/query")
async def query_documents(request: QueryRequest):
    try:
        # Aquí implementarías tu lógica de RAG
        # Este es un ejemplo básico que devuelve la pregunta
        return {
            "question": request.question,
            "answer": "Esta es una respuesta de ejemplo. Implementa tu lógica RAG aquí."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}