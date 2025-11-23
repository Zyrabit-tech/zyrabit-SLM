import os
import chromadb
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import sys

# --- Configuración ---
SOURCE_DIRECTORY = "document_source"
CHROMA_HOST = "localhost"
CHROMA_PORT = 8001
COLLECTION_NAME = "libros_tecnicos"
EMBEDDING_MODEL = "mxbai-embed-large" # Asegúrate de tener este modelo con `ollama pull mxbai-embed-large`

# --- Configuración del Chunking (El "Sweet Spot") ---
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

def check_ollama_model(model_name):
    """Verifica si el modelo de embeddings está disponible en Ollama."""
    print(f"Verificando si el modelo '{model_name}' está disponible en Ollama...")
    try:
        # Intenta inicializar el modelo. Esto fallará si Ollama no está corriendo o el modelo no existe.
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
    """Carga y lee los PDFs del directorio fuente."""
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
    """Divide los documentos en chunks."""
    print(f"\nDividiendo documentos en chunks (Tamaño: {CHUNK_SIZE}, Superposición: {CHUNK_OVERLAP})...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    chunks = text_splitter.split_documents(docs)
    print(f"División completa. Número total de chunks: {len(chunks)}")
    return chunks

def populate_vector_db(chunks, embeddings):
    """Conecta a ChromaDB y puebla la base de datos."""
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

    # Convertir documentos de LangChain a algo que Chroma pueda ingestar (texto y metadatos)
    documents_to_add = [chunk.page_content for chunk in chunks]
    metadatas_to_add = [chunk.metadata for chunk in chunks]
    # Crear IDs únicos para cada chunk
    ids_to_add = [f"chunk_{i}" for i in range(len(chunks))]

    print(f"Iniciando ingesta de {len(chunks)} chunks... Esto puede tardar varios minutos.")
    
    # Chroma ingesta en batches.
    # El cliente `add` se encarga de los embeddings si le pasamos los documentos.
    # ¡PERO! Es mejor usar los embeddings de LangChain para consistencia.
    
    print("Generando embeddings con Ollama... (Esto es lo que más tarda)")
    embedded_chunks = embeddings.embed_documents(documents_to_add)

    print(f"Embeddings generados. Añadiendo a la colección en batches...")
    
    # Añadir a la colección en batches para no sobrecargar
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
    
    # 1. Verificar Ollama
    if not check_ollama_model(EMBEDDING_MODEL):
        sys.exit(1)
        
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)

    # 2. Cargar Documentos
    docs = load_documents(SOURCE_DIRECTORY)
    if not docs:
        print("No hay documentos para procesar. Saliendo.")
        sys.exit(1)

    # 3. Dividir Documentos
    chunks = split_documents(docs)

    # 4. Poblar la Base de Datos
    populate_vector_db(chunks, embeddings)

if __name__ == "__main__":
    main()