# Zyrabit SLM Secure Suite (v1.0‑beta)

[![Spanish](https://img.shields.io/badge/lang-Spanish-blue.svg)](README.md)
![Python](https://img.shields.io/badge/python-v3.10%2B-blue.svg)
![Docker](https://img.shields.io/badge/docker--compose-ready-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)
![Architecture](https://img.shields.io/badge/architecture-clean-orange.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)
-----

## 📖 Description

**Zyrabit SLM Secure Suite** is a local AI solution that combines **Small Language Models (SLMs)** with a Retrieval-Augmented Generation (RAG) engine and a **Zero-Trust** security layer.

### 🧬 Our Philosophy

  * **Efficiency**: Optimized execution for consumer hardware (Mac M1/M2, Consumer GPUs).
  * **Speed**: Lower latency thanks to compact models (Phi-3, Mistral).
  * **Sovereignty**: Your data never leaves your infrastructure. Everything runs locally.

-----

## 🛠️ Validated Environment

| Platform | CPU | RAM | OS |
|------------|-----|-----|----|
| MacBook Pro (M1 Pro) | 8‑core | 16 GB | macOS Sequoia 15.1 |
| Linux (Ubuntu 22.04) | 4‑core | 8 GB | - |
| Windows (WSL2) | 4‑core | 8 GB | - |

> **Windows Note:** Use WSL2 to run Docker and scripts.

-----

## 📦 Installation

1.  **Prerequisites**
      - Docker & Docker‑Compose
      - Python 3.10 +
      - `git` (optional)
2.  **Clone the repository**
    ```bash
    git clone https://github.com/Zyrabit-tech/zyrabit-llm.git
    cd zyrabit-SLM
    ```
3.  **Virtual Environment**
    ```bash
    python -m venv .venv
    source .venv/bin/activate   # macOS / Linux
    # .venv\Scripts\activate   # Windows
    pip install -r requirements.txt
    ```
4.  **Infrastructure**
    ```bash
    cd zyrabit-brain-api
    docker compose up -d   # spins up slm-engine, vector‑db and api‑rag
    cd ..
    ```
5.  **Download Required Models**
    ```bash
    chmod +x setup_slm.sh
    ./setup_slm.sh   # verifies Docker, starts slm-engine and downloads phi3, kimi‑k2‑thinking:cloud and mxbai‑embed‑large
    ```
6.  **Run the UI**
    ```bash
    streamlit run slm_console.py
    ```
    Access at `http://localhost:8501`.

-----

## 🚀 Quick Usage

```bash
# Secure CLI
python secure_agent.py "My email is john@example.com and my balance is $1,200.00"
```

The agent will display the original prompt, the sanitized prompt, and the model's response.

-----

## 🧪 Tests

Run the test suite with:

```bash
pytest -q
```

Tests cover PII sanitization and backend response validation.

-----

## 📜 License

MIT © Zyrabit 2025