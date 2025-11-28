# Zyrabit LLM Secure Suite
[![Spanish](https://img.shields.io/badge/lang-Español-red.svg)](README.md)
![Python](https://img.shields.io/badge/python-v3.10+-blue.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)
![Docker](https://img.shields.io/badge/docker--compose-ready-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)
![Architecture](https://img.shields.io/badge/architecture-clean-orange.svg)

**Zyrabit LLM Secure Suite** is a reference architecture for deploying secure and private Generative AI agents in enterprise environments. It combines the power of **Ollama (Phi-3)** with an intermediate security layer that sanitizes sensitive data before it touches the LLM.

## Architecture



## Value Proposition

1.  **Privacy by Design**: No PII data (Emails, Phones, Credit Cards) reaches the language model. The secure agent acts as a data firewall.
2.  **Data Sovereignty**: 100% local or on-premise execution using efficient models like Phi-3.
3.  **Full Observability**: Integrated monitoring stack to trace latency, token usage, and errors in real-time.
4.  **Modular Architecture**: Decoupled components (Client, API, LLM, VectorDB) allowing independent scaling.

## Installation

### Prerequisites
*   Docker & Docker Compose
*   Python 3.10+
*   Ollama (for local execution without Docker)

### Quick Start

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Zyrabit-tech/zyrabit-llm.git
    cd zyrabit-llm
    ```

2.  **Setup Environment**:
    ```bash
    # Install Python dependencies
    pip install -r requirements.txt
    
    # Setup Ollama and download models (phi3 + mxbai-embed-large)
    chmod +x setup_ollama.sh
    ./setup_ollama.sh
    ```

3.  **Document Ingestion (RAG)**:
    To feed the vector memory with your own documents:
    1.  Place your PDF files in the `document_source` folder.
    2.  Run the advanced ingestion script:
        ```bash
        python3 ingest/ingest.py
        ```
    This script uses `PyPDFLoader` to process documents and `mxbai-embed-large` to automatically generate high-quality embeddings.

4.  **Run Secure Agent**:
    ```bash
    python3 secure_agent.py
    ```

## Troubleshooting

*   **Ollama Connection Error**: Ensure Ollama is running (`ollama serve`) and listening on port 11434.
*   **Model Not Found**: Run `./setup_ollama.sh` to ensure `phi3` and `mxbai-embed-large` are downloaded.
*   **Execution Permissions**: If `setup_ollama.sh` fails, make sure you ran `chmod +x setup_ollama.sh`.

## Contributing

We want your help to make Zyrabit LLM better!
Please read our [Contribution Guidelines](CONTRIBUTING_EN.md) to learn about our workflow, commit convention, and how to get started.

**Remember**: Pull Requests must target the `beta` branch.
