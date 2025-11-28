import os
import chromadb
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import sys

# --- Configuration ---
SOURCE_DIRECTORY = "document_source"
CHROMA_HOST = "localhost"
CHROMA_PORT = 8001
COLLECTION_NAME = "libros_tecnicos"
EMBEDDING_MODEL = "mxbai-embed-large" # Make sure to have this model with `ollama pull mxbai-embed-large`

# --- Chunking Configuration (The "Sweet Spot") ---
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

def check_ollama_model(model_name):
    """Verifies if the embedding model is available in Ollama."""
    print(f"Verificando si el modelo '{model_name}' está disponible en Ollama...")
    try:
        # Attempts to initialize the model. This will fail if Ollama is not running or the model does not exist.
        OllamaEmbeddings(model=model_name).embed_query("test")
        print(f"¡Éxito! Modelo '{model_name}' está listo.")
        return True
    except Exception as e:
        print("\n--- ¡ERROR! ---")
        print(f"No se pudo conectar o usar el modelo '{model_name}' de Ollama.")
        print("Asegúrate de que Ollama esté corriendo y hayas ejecutado:")
        print(f"  ollama pull {model_name}")
        print(f"Error original: {e}")
        return False

def load_documents(source_dir):
    """Loads and reads PDFs from the source directory."""
    print(f"\nCargando documentos desde: '{source_dir}'")
    if not os.path.exists(source_dir):
        print(f"Error: El directorio '{source_dir}' no existe. Por favor, créalo y añada sus PDFs.")
        sys.exit(1)
        
    pdf_files = [f for f in os.listdir(source_dir) if f.endswith(".pdf")]
    
    if not pdf_files:
        print(f"Error: No se encontraron archivos PDF en '{source_dir}'.")
        print("Asegúrese de haber colocado sus archivos (ej. 'Clean Architecture.pdf') allí.")
        sys.exit(1)

    print(f"Se encontraron {len(pdf_files)} archivos PDF. Iniciando carga...")
    
    all_docs = []
    for pdf_file in pdf_files:
        path = os.path.join(source_dir, pdf_file)
        try:
            loader = PyPDFLoader(path)
            docs = loader.load()
            print(f"  - Cargado: {pdf_file} ({len(docs)} páginas)")
            all_docs.extend(docs)
        except Exception as e:
            print(f"Error cargando '{pdf_file}': {e}. Saltando archivo.")
            
    print(f"Carga completa. Total de páginas cargadas: {len(all_docs)}")
    return all_docs

def split_documents(docs):
    """Splits documents into chunks."""
    print(f"\nDividiendo documentos en chunks (Tamaño: {CHUNK_SIZE}, Superposición: {CHUNK_OVERLAP})...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    chunks = text_splitter.split_documents(docs)
    print(f"División completa. Número total de chunks: {len(chunks)}")
    return chunks

def populate_vector_db(chunks, embeddings):
    """Connects to ChromaDB and populates the database."""
    print(f"\nConectando a ChromaDB en {CHROMA_HOST}:{CHROMA_PORT}...")
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        print("Conexión a ChromaDB exitosa.")
    except Exception as e:
        print(f"Error conectando a ChromaDB: {e}")
        print("Asegúrate de que el stack de Docker esté corriendo ('docker compose up -d')")
        print(f"Y que el puerto {CHROMA_PORT} esté expuesto por el contenedor 'vector-db'.")
        sys.exit(1)

    print(f"Obteniendo o creando la colección: '{COLLECTION_NAME}'")
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    # Convert LangChain documents to something Chroma can ingest (text and metadata)
    documents_to_add = [chunk.page_content for chunk in chunks]
    metadatas_to_add = [chunk.metadata for chunk in chunks]
    # Create unique IDs for each chunk
    ids_to_add = [f"chunk_{i}" for i in range(len(chunks))]

    print(f"Iniciando ingesta de {len(chunks)} chunks... Esto puede tardar varios minutos.")
    
    # Chroma ingests in batches.
    # The `add` client handles embeddings if we pass the documents.
    # BUT! It is better to use LangChain embeddings for consistency.
    
    print("Generando embeddings con Ollama... (Esto es lo que más tarda)")
    embedded_chunks = embeddings.embed_documents(documents_to_add)

    print(f"Embeddings generados. Añadiendo a la colección en batches...")
    
    # Add to collection in batches to avoid overloading
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch_end = min(i + batch_size, len(chunks))
        print(f"  - Añadiendo batch {i//batch_size + 1} (chunks {i} a {batch_end-1})...")
        
        collection.add(
            embeddings=embedded_chunks[i:batch_end],
            documents=documents_to_add[i:batch_end],
            metadatas=metadatas_to_add[i:batch_end],
            ids=ids_to_add[i:batch_end]
        )

    print("\n--- ¡Ingesta Completa! ---")
    count = collection.count()
    print(f"La colección '{COLLECTION_NAME}' ahora contiene {count} chunks.")
    print("¡La 'gasolina' está cargada! Ya puedes hacer consultas RAG reales.")

def main():
    print("--- Iniciando Script de Ingesta RAG-Ops ---")
    
    # 1. Verify Ollama
    if not check_ollama_model(EMBEDDING_MODEL):
        sys.exit(1)
        
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)

    # 2. Load Documents
    docs = load_documents(SOURCE_DIRECTORY)
    if not docs:
        print("No hay documentos para procesar. Saliendo.")
        sys.exit(1)

    # 3. Split Documents
    chunks = split_documents(docs)

    # 4. Populate Database
    populate_vector_db(chunks, embeddings)

if __name__ == "__main__":
    main()