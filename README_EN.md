# Zyrabit LLM Secure Suite

![Python](https://img.shields.io/badge/python-v3.10+-blue.svg)
![Docker](https://img.shields.io/badge/docker-compose-ready-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)
![Architecture](https://img.shields.io/badge/architecture-clean-orange.svg)

## 📖 Project Description

**Zyrabit** is a complete **Zero-Trust** AI solution that combines:
- A local **Ollama server** (`phi3` model – replacing `mistral`).
- A **Python client** (`secure_agent.py`) that **sanitizes** any prompt before sending it to the model, preventing leakage of sensitive data (PII, credit cards, amounts).
- An **interactive dashboard** built with **Streamlit** (`app.py`) that displays the original and sanitized prompts side-by-side, and visualizes the model's response.
- A **Docker-Compose environment** that orchestrates the RAG API, Ollama, ChromaDB, Prometheus, and Grafana.

The goal is to demonstrate how to integrate **offensive cybersecurity** into generative AI workflows without sacrificing usability.

---

## 💰 Why Zyrabit (Value Proposition)

| Feature | 🚫 Public AI (ChatGPT/Claude) | ✅ Zyrabit (Local & Secure) |
| :--- | :--- | :--- |
| **Data Leakage** | High Risk (Your data trains their models) | **Zero Risk** (Local Sanitization + Air-Gapped) |
| **Cloud Costs** | Recurring ($20/month per user) | **$0 / month** (Runs on your own hardware) |
| **Hardware** | Dependent on external servers | **Optimized** (Runs on consumer CPU/GPU) |
| **Privacy** | Black Box | **Auditable** (100% Open Source) |

---

## ✨ Key Features

- **Automatic sanitization** of emails, credit card numbers, and dollar amounts using regular expressions.
- **Exposed Ollama port (11434)** allowing local scripts to communicate with the model.
- **Automatic installation** of the `phi3` model via the `setup_ollama.sh` script.
- **Graphical interface** with Streamlit showing text before and after sanitization side-by-side.
- **Monitoring** with Prometheus and Grafana (ports 9091 and 3000).
- **Persistence** of models and vectors via Docker volumes (`./ollama-models`, `./chroma-data`).

---

## 🏗️ Architecture

```mermaid
graph TD
    subgraph "Secure Client (Local Python)"
        User((👤 User))
        Agent[🕵️ secure_agent.py<br/>(Sanitizer Regex/NER)]
        UI[🖥️ app.py<br/>(Streamlit Dashboard)]
    end

    subgraph "Zyrabit Core (Docker Network)"
        API[⚡ api-rag<br/>(FastAPI Gateway)]
        LLM[🧠 llm-server<br/>(Ollama - Phi3)]
        VectorDB[(🗄️ ChromaDB<br/>Vector Memory)]
        Monitor[📊 Grafana + Prometheus<br/>Observability]
    end

    User --> UI
    UI -->|1. Raw Prompt| Agent
    Agent -->|2. Redacted Data| API
    API -->|3. Vector Query| VectorDB
    VectorDB -->|4. Context| API
    API -->|5. Final Prompt| LLM
    LLM -->|6. Response| API
    API -->|7. Secure Display| UI

    style Agent fill:#ff9900,stroke:#333,stroke-width:2px
    style LLM fill:#99ff99,stroke:#333,stroke-width:2px
```

---

## 🚀 Installation and Setup

### 1️⃣ Prerequisites

- **Docker & Docker-Compose**
- **Python 3.9+**
- **pip** (use `python3 -m pip` to avoid PATH issues)

### 2️⃣ Clone the Repository

```bash
git clone https://github.com/your-username/zyrabit-llm.git
cd zyrabit-llm
```

### 3️⃣ Install Python Dependencies

```bash
python3 -m pip install --user requests streamlit watchdog
```
> *Note:* `streamlit` is installed in `~/Library/Python/3.9/bin`. Add that path to your `$PATH` if you wish to use the command directly:
```bash
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
```

### 4️⃣ Start Docker Containers

```bash
docker-compose up -d
```
This will create the services `api-rag`, `llm-server`, `vector-db`, `prometheus`, and `grafana`.

### 5️⃣ Download the Model

Run the setup script (automatically downloads the `phi3` model):

```bash
chmod +x setup_ollama.sh
./setup_ollama.sh
```
The script checks if the model is already installed and, if not, downloads it.

### 6️⃣ Test the Secure Client

```bash
python3 secure_agent.py
```
You should see two test cases: an innocent question and one with sensitive data that gets redacted.

### 7️⃣ Run the Streamlit UI

```bash
streamlit run app.py --server.headless true
```
Open `http://localhost:8501` in your browser. The sidebar shows configuration, and the main panel allows you to enter prompts and see the sanitized text and model response.

---

## 🚑 Troubleshooting

| Issue | Possible Solution |
| :--- | :--- |
| **Error: Connection refused** | Ensure Docker is running (`docker ps`) and port 11434 is free. |
| **Model not responding** | Run `./setup_ollama.sh` again to verify `phi3` downloaded correctly. |
| **Streamlit not found** | Check your PATH or run `python3 -m streamlit run app.py`. |
| **Permission denied** | Run `chmod +x setup_ollama.sh` before running the script. |

---

## 📄 License

This project is licensed under the **MIT License**. You can use, modify, and distribute the code, even for commercial purposes, provided you keep the original license notice.

---

## 🙌 Contributions

Contributions are welcome. Please open a *pull request* describing your changes and ensuring all tests pass.

---

## 📞 Contact

**Zyrabit Systems** – https://zyrabit.com
