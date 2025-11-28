# Zyrabit LLM Secure Suite
[![Spanish](https://img.shields.io/badge/lang-Español-red.svg)](README.md)
![Python](https://img.shields.io/badge/python-v3.10+-blue.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)
![Docker](https://img.shields.io/badge/docker--compose-ready-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)
![Architecture](https://img.shields.io/badge/architecture-clean-orange.svg)

**Zyrabit LLM Secure Suite** is a reference architecture for deploying secure and private Generative AI agents in enterprise environments. It combines the power of **Ollama (Phi-3)** with an intermediate security layer that sanitizes sensitive data before it touches the LLM.

## 🎯 Value Proposition

1.  **Privacy by Design**: No PII data (Emails, Phones, Credit Cards) reaches the language model. The secure agent acts as a data firewall.
2.  **Data Sovereignty**: 100% local or on-premise execution using efficient models like Phi-3.
3.  **Full Observability**: Integrated monitoring stack to trace latency, token usage, and errors in real-time.
4.  **Modular Architecture**: Decoupled components (Client, API, LLM, VectorDB) allowing independent scaling.

## 🏗️ Architecture

The project is divided into two main components:

1.  **Frontend (Root)**:
    *   `app.py`: Streamlit dashboard for user interaction.
    *   `secure_agent.py`: CLI agent for quick and secure testing.
2.  **Backend (`zyrabit-brain-api`)**:
    *   `api-rag/`: FastAPI API that orchestrates RAG logic, connects with ChromaDB and Ollama.

## 🐍 Quick Setup (Local)

### Prerequisites
*   **Python 3.10+**
*   **Docker** (for the full stack with ChromaDB and Prometheus)

### ✅ Validated Specifications

This project has been tested and validated on the following configuration:

| Component | Validation Specification |
|-----------|--------------------------|
| Base Hardware | MacBook Pro (Apple Silicon M1 Pro) |
| RAM | 16 GB (Unified Memory) |
| Operating System | macOS Sequoia 15.1 (Build 25B78) |
| Python | Version 3.9+ / 3.10+ |


### ⚠️ Compatibility Notes

**Windows Users:** We strongly recommend using **WSL2** (Windows Subsystem for Linux). Bash scripts (`.sh`) and Docker network management work natively in WSL2. Running this directly in PowerShell may require manual adjustments.

**Linux Users:** Natively compatible with Ubuntu 22.04+ and Debian 11+.

**Architecture:** Docker images are built for `linux/amd64` and `linux/arm64`, ensuring compatibility on both Intel/AMD servers and ARM architectures (Apple Silicon, AWS Graviton).

### Installation Steps

1.  **Configure Python Environment**:
    ```bash
    # Create virtual environment
    python3 -m venv .venv

    # Activate environment (Mac/Linux)
    source .venv/bin/activate
    # Windows (WSL2 recommended or PowerShell):
    # .\.venv\Scripts\activate

    # Install dependencies
    pip3 install -r requirements.txt
    ```

2.  **Spin up Infrastructure (Docker)**:
    This step starts the brain (API), memory (Chroma), and engine (Ollama).
    ```bash
    cd zyrabit-brain-api
    docker compose up -d
    cd ..
    ```

3.  **Initialize AI Models**:
    Once Docker is running, download the necessary models (`phi3` and `mxbai-embed-large`).
    ```bash
    chmod +x setup_ollama.sh
    ./setup_ollama.sh
    ```

4.  **Launch! 🚀**:
    ```bash
    streamlit run app.py
    ```

## 📚 Document Ingestion (RAG)

To feed the vector memory with your own documents, use the API endpoint:

**Option A: Via cURL**
```bash
curl -X POST "http://localhost:8080/v1/ingest" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@/path/to/your/document.pdf"
```

**Option B: Via Swagger Interface**
1.  Open `http://localhost:8080/docs` in your browser.
2.  Find the `POST /v1/ingest` endpoint.
3.  Upload your PDF file (Max 800MB).

The system will process the PDF, generate embeddings with `mxbai-embed-large`, and save them to ChromaDB automatically.

## 🐳 Docker Deployment (Optional)

To run the full stack with ChromaDB, Prometheus, and Grafana:

```bash
cd zyrabit-brain-api
docker compose up -d
```

See [zyrabit-brain-api/README.md](zyrabit-brain-api/README.md) for more details about the Docker architecture.

## 🛠️ Troubleshooting

*   **Ollama Connection Error**: Ensure Ollama is running (`ollama serve`) and listening on port 11434.
*   **Model Not Found**: Run `./setup_ollama.sh` to ensure `phi3` and `mxbai-embed-large` are downloaded.
*   **Execution Permissions**: If `setup_ollama.sh` fails, make sure you ran `chmod +x setup_ollama.sh`.
*   **Virtual environment not active**: Verify that your terminal prompt shows `(.venv)` at the beginning.

## 🤝 Contributing

We want your help to make Zyrabit LLM better!
Please read our [Contribution Guidelines](CONTRIBUTING_EN.md) to learn about our workflow, commit convention, and how to get started.

**Remember**: Pull Requests must target the `beta` branch.

## 📄 License

This project is licensed under the [MIT License](LICENSE).
