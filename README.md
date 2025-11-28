# Zyrabit LLM Secure Suite
[![English](https://img.shields.io/badge/lang-English-blue.svg)](README_EN.md)
![Python](https://img.shields.io/badge/python-v3.10+-blue.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)
![Docker](https://img.shields.io/badge/docker--compose-ready-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)
![Architecture](https://img.shields.io/badge/architecture-clean-orange.svg)

**Zyrabit LLM Secure Suite** es una arquitectura de referencia para desplegar agentes de IA generativa seguros y privados en entornos empresariales. Combina la potencia de **Ollama (Phi-3)** con una capa de seguridad intermedia que sanitiza datos sensibles antes de que toquen el LLM.

## 🎯 Propuesta de Valor

1.  **Privacidad por Diseño**: Ningún dato PII (Emails, Teléfonos, Tarjetas de Crédito) llega al modelo de lenguaje. El agente seguro actúa como un firewall de datos.
2.  **Soberanía de Datos**: Ejecución 100% local u on-premise utilizando modelos eficientes como Phi-3.
3.  **Observabilidad Completa**: Stack de monitoreo integrado para trazar latencia, uso de tokens y errores en tiempo real.
4.  **Arquitectura Modular**: Componentes desacoplados (Cliente, API, LLM, VectorDB) que permiten escalar independientemente.

## 🏗️ Arquitectura

El proyecto se divide en dos componentes principales:

1.  **Frontend (Raíz)**:
    *   `app.py`: Dashboard de Streamlit para interacción con el usuario.
    *   `secure_agent.py`: Agente CLI para pruebas rápidas y seguras.
2.  **Backend (`zyrabit-brain-api`)**:
    *   `api-rag/`: API FastAPI que orquesta la lógica de RAG, conecta con ChromaDB y Ollama.

## 🐍 Instalación Rápida (Local)

### Prerrequisitos
*   **Python 3.10+**
*   **Docker** (para el stack completo con ChromaDB y Prometheus)

### ✅ Especificaciones Validadas

Este proyecto ha sido probado y validado en la siguiente configuración:

| Componente | Especificación de Validación |
|------------|------------------------------|
| Hardware Base | MacBook Pro (Apple Silicon M1 Pro) |
| Memoria RAM | 16 GB (Unified Memory) |
| Sistema Operativo | macOS Sequoia 15.1 (Build 25B78) |
| Python | Versión 3.9+ / 3.10+ |


### ⚠️ Notas de Compatibilidad

**Usuarios de Windows:** Recomendamos encarecidamente usar **WSL2** (Windows Subsystem for Linux). Los scripts de bash (`.sh`) y la gestión de redes de Docker funcionan de forma nativa en WSL2. Ejecutar esto en PowerShell directo puede requerir ajustes manuales.

**Usuarios de Linux:** Compatible nativamente con Ubuntu 22.04+ y Debian 11+.

**Arquitectura:** Las imágenes de Docker están construidas para `linux/amd64` y `linux/arm64`, asegurando compatibilidad tanto en servidores Intel/AMD como en arquitecturas ARM (Apple Silicon, AWS Graviton).

### Pasos de Instalación

1.  **Configurar Entorno Python**:
    ```bash
    # Crear entorno virtual
    python3 -m venv .venv

    # Activar entorno (Mac/Linux)
    source .venv/bin/activate
    # Windows (WSL2 recomendado o PowerShell):
    # .\.venv\Scripts\activate

    # Instalar dependencias
    pip3 install -r requirements.txt
    ```

2.  **Levantar Infraestructura (Docker)**:
    Este paso enciende el cerebro (API), la memoria (Chroma) y el motor (Ollama).
    ```bash
    cd zyrabit-brain-api
    docker compose up -d
    cd ..
    ```

    **Configuración Opcional**: Si necesitas personalizar variables de entorno (URLs, nombres de modelos, etc.):
    ```bash
    cd zyrabit-brain-api
    cp .env.example .env
    # Edita .env con tus valores personalizados
    ```
    
    Variables clave disponibles:
    - `OLLAMA_BASE_URL`: URL del servidor Ollama (default: `http://llm-server:11434`)
    - `MODEL_NAME`: Modelo LLM a usar (default: `phi3`)
    - `VECTOR_DB_HOST`: Host de ChromaDB (default: `vector-db`)
    - `ENABLE_PII_SANITIZATION`: Activar sanitización de datos sensibles (default: `True`)

3.  **Inicializar Modelos de IA**:
    Una vez que Docker esté corriendo, descarga los modelos necesarios (`phi3` y `mxbai-embed-large`).
    ```bash
    chmod +x setup_ollama.sh
    ./setup_ollama.sh
    ```

4.  **¡Despegue! 🚀**:
    ```bash
    streamlit run app.py
    ```

## 📚 Ingesta de Documentos (RAG)

Para alimentar la memoria vectorial con tus propios documentos, utiliza el endpoint de la API:

**Opción A: Vía cURL**
```bash
curl -X POST "http://localhost:8080/v1/ingest" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@/ruta/a/tu/documento.pdf"
```

**Opción B: Vía Interfaz Swagger**
1.  Abre `http://localhost:8080/docs` en tu navegador.
2.  Busca el endpoint `POST /v1/ingest`.
3.  Sube tu archivo PDF (Máx 800MB).

El sistema procesará el PDF, generará embeddings con `mxbai-embed-large` y los guardará en ChromaDB automáticamente.

Consulta [zyrabit-brain-api/README.md](zyrabit-brain-api/README.md) para más detalles sobre la arquitectura Docker.

## 🛠️ Troubleshooting

*   **Error de conexión con Ollama**: Asegúrate de que Ollama esté corriendo (`ollama serve`) y escuchando en el puerto 11434.
*   **Modelo no encontrado**: Ejecuta `./setup_ollama.sh` para asegurar que `phi3` y `mxbai-embed-large` estén descargados.
*   **Permisos de ejecución**: Si `setup_ollama.sh` falla, asegúrate de haber ejecutado `chmod +x setup_ollama.sh`.
*   **Entorno virtual no activo**: Verifica que el prompt de tu terminal muestre `(.venv)` al inicio.

## 🤝 Contribución

¡Queremos tu ayuda para hacer Zyrabit LLM mejor!
Por favor lee nuestras [Guías de Contribución](CONTRIBUTING.md) para conocer nuestro flujo de trabajo, convención de commits y cómo empezar.

**Recuerda**: Los Pull Requests deben apuntar a la rama `beta`.

## 📄 Licencia

Este proyecto está bajo la [Licencia MIT](LICENSE).