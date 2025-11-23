import chromadb
from chromadb.config import Settings
import sys
import os
from pathlib import Path

def main():
    # Conexión a ChromaDB (usando el puerto expuesto 8001)
    client = chromadb.HttpClient(host="localhost", port=8001)
    
    # Crea o obtiene una colección
    collection = client.create_collection(
        name="documentos",
        metadata={"description": "Documentos para RAG"}
    )
    
    # TODO: Implementa aquí tu lógica de ingesta
    # 1. Lee los documentos
    # 2. Genera embeddings
    # 3. Guárdalos en ChromaDB
    print("¡Script de ingesta listo! Implementa tu lógica aquí.")

if __name__ == "__main__":
    main()