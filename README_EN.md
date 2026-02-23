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

Ultra-fast bootstrap installer:

```bash
curl -sSL https://zyrabit.com/install.sh | bash
```

Or local setup:

1.  **Prerequisites**
      - Docker & Docker‑Compose
      - Python 3.10 +
      - `git` (optional)
2.  **Clone the repository**
    ```bash
    git clone https://github.com/Zyrabit-tech/zyrabit-SLM.git
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
    chmod +x zyra-up.sh
    ./zyra-up.sh install
    ```
5.  **Installer command modes**
    ```bash
    ./zyra-up.sh doctor   # validate environment profile
    ./zyra-up.sh start    # start infrastructure only
    ./zyra-up.sh install  # start stack + pull base models
    ```
    The script auto-detects NVIDIA/Metal/CPU and defaults to `qwen2.5:7b` (`qwen2.5:1.5b` on low-RAM machines).
    
    Official setup scripts:
    - `install.sh`: remote/local bootstrap (clones repo and runs `zyra-up.sh install`)
    - `zyra-up.sh`: main installer and stack orchestrator
    
    Manual model pull (without running `install`):
    ```bash
    docker compose -f zyrabit-brain-api/docker-compose.yml up -d slm-engine
    docker compose -f zyrabit-brain-api/docker-compose.yml exec -T slm-engine ollama pull qwen2.5:7b
    docker compose -f zyrabit-brain-api/docker-compose.yml exec -T slm-engine ollama pull mxbai-embed-large
    ```
6.  **Run the UI**
    ```bash
    streamlit run slm_console.py
    ```
    Access at `http://localhost:8501`.

## Air-Gapped Installation (high priority)

For isolated US/EU environments:

1. On an internet-connected workstation, pull required images:
   ```bash
   docker pull traefik:latest
   docker pull ollama/ollama:latest
   docker pull chromadb/chroma:latest
   docker pull prom/prometheus:latest
   docker pull grafana/grafana:latest
   docker pull n8nio/n8n:latest
   ```
2. Export them as a transport bundle:
   ```bash
   docker save -o zyrabit-images.tar \
     traefik:latest ollama/ollama:latest chromadb/chroma:latest \
     prom/prometheus:latest grafana/grafana:latest n8nio/n8n:latest
   ```
3. Move `zyrabit-images.tar` via controlled USB media.
4. Load images on the offline server:
   ```bash
   docker load -i zyrabit-images.tar
   ```
5. Start the stack without internet egress:
   ```bash
   ./zyra-up.sh start
   ```

Enterprise alternative: mirror signed images into an on-prem local registry (Harbor/Nexus/Artifactory) and pull from that registry only.

-----

## 🚀 Quick Usage

```bash
# Secure CLI
python secure_agent.py "My email is john@example.com and my balance is $1,200.00"
```

The agent applies reversible token anonymization (`<USER_EMAIL_1>`, etc.) before inference and restores values for the final user response.

## 🔐 Network and ingress hardening

- Traefik reverse proxy as single public entrypoint (`https://localhost`).
- HTTP→HTTPS redirection plus request rate limiting.
- Observability is exposed via Traefik routes (`/grafana`, `/prometheus`) with required basic auth variables.
- Segmented Docker networks:
  - `frontend-network`
  - `backend-network`
  - `model-network` with `internal: true`

## 📈 Observability

Prometheus metrics on `/metrics`, including:

- `zyrabit_token_latency_ms_per_token`
- `zyrabit_token_usage_total`
- `zyrabit_security_hits_total`

## 🔌 MCP Bridge

- Standard config file: `mcp/config.json`
- API config endpoint: `GET /mcp/config.json`
- MCP JSON-RPC endpoint: `POST /mcp`
- Bridge operations are sanitization-first by design.

## 📚 Docs portal

An optional Docusaurus docs container is included:

```bash
cd zyrabit-brain-api
docker compose --profile docs up -d docs-portal
```

A machine-friendly technical digest is available in `llms-full.md`.

## 🧭 Documentation map (non-overlapping)

Each README has a clear scope:

- `README.md`: product-level overview, quick setup, and global usage.
- `README_EN.md` (this file): English mirror of the root README.
- `zyrabit-brain-api/README.md`: backend operations (compose, endpoints, networks, profiles).
- `zyrabit-brain-api/README_EN.md`: English mirror of backend operations.

Maintenance rule:

- root docs for onboarding and global workflows.
- backend docs for API/infrastructure internals.
- avoid copy-pasting full sections between root and backend; link when needed.

-----

## 🧪 Tests

Run the test suite with:

```bash
cd zyrabit-brain-api/api-rag
python3 -m pytest -q
```

Tests cover PII sanitization, endpoint integration, secure model payload flow, and MCP contract checks.

-----

## 📜 License

MIT © Zyrabit 2025