# Zyrabit Platform | The Sovereign AI Infrastructure Layer

[![Docker Pulls](https://img.shields.io/docker/pulls/zyrabitcore/zyrabit-slm?style=for-the-badge&color=4ecdc4&logo=docker&logoColor=white)](https://hub.docker.com/r/zyrabitcore/zyrabit-slm)
[![GitHub Stars](https://img.shields.io/github/stars/Zyrabit-tech/zyrabit-SLM?style=for-the-badge&color=6090b4&logo=github)](https://github.com/Zyrabit-tech/zyrabit-SLM)
[![License: MIT](https://img.shields.io/badge/License-MIT-3f5a6d?style=for-the-badge)](https://github.com/Zyrabit-tech/zyrabit-SLM/blob/main/LICENSE)

> **Artificial Intelligence is critical infrastructure. Critical infrastructure should not be rented.**

Zyrabit Platform is the open-source, local-first operating system for **Sovereign Enterprise AI**. It transforms your local models (Ollama, vLLM, LM Studio, Tenstorrent) into an enterprise-grade AI system with automatic PII anonymization, citation-backed document retrieval, and verifiable audit trails — **100% offline, with zero cloud dependencies.**

---

## ⚡ 60-Second Quickstart

### If you already have Ollama / vLLM running on your machine

Run Zyrabit as an intelligent privacy gateway connected to your host engine:

```bash
docker run -d \
  --name zyrabit-platform \
  -p 8080:8080 \
  --add-host=host.docker.internal:host-gateway \
  -e INFERENCE_PROVIDER=ollama \
  -e SLM_URL=http://host.docker.internal:11434 \
  -v zyrabit_vault:/app/db_data \
  zyrabitcore/zyrabit-slm:latest
```

Open **[http://localhost:8080](http://localhost:8080)** in your browser.

*Works seamlessly across **macOS (Apple Silicon)**, **Linux (Ubuntu/Debian)**, and **Windows (WSL2)**.*

---

## 🎥 Watch it in Action: 100% Air-Gapped Sovereign AI

See Zyrabit Platform running completely offline, processing voice commands and extracting intelligence from documents in real time without a single external API or internet ping:

👉 **[Watch the Offline Demo Video (MP4)](https://assets.zyrabit.com/streaming/zyrabit_ocrtex_bot.mp4)**  
*(Video audio in Spanish — showcases live offline OCR & voice transcription)*

---

## 🛡️ Why Zyrabit Platform? (The Missing Enterprise Layer)

Running raw Ollama or vLLM in a business exposes you to serious legal and operational risks. Zyrabit sits as the secure operating layer on top:

| The Problem with Raw Models | How Zyrabit Platform Solves It |
| --- | --- |
| **Data Leaks & Compliance** | **Zero-Leak PII Shield:** Automatically detects and masks names, government IDs (RFC, CURP, SSN), credit cards, and emails *before* prompts reach inference, restoring them on response. |
| **Model Hallucinations** | **Evidence-Bound RAG ("Citation or Silence"):** Combines BM25 lexical keyword search with ChromaDB vectors. Answers link to the exact page/paragraph of the source document; if no evidence exists, the system abstains. |
| **Multimodal Ingestion** | **Audio & Document Pipeline:** Drag and drop PDFs, DOCX, scans (OCR), and audio voice notes (via local Whisper transcription) directly into your private knowledge base. |
| **Model & Hardware Lock-In** | **Hexagonal Pluggability:** Swap between Ollama, vLLM, llama.cpp, or Tenstorrent NPUs (Blackhole/Wormhole) without modifying a single line of application code. |
| **Audit & Trazability** | **Sovereign Persistence:** SQLite WAL audit ledger tracks all interactions, document versions, and access policies locally. |

---

## 🔌 Connecting to Any Local Inference Provider

Zyrabit Platform is engine-agnostic:

### Connect to Ollama

```bash
-e INFERENCE_PROVIDER=ollama \
-e SLM_URL=http://host.docker.internal:11434 \
-e MODEL_NAME=qwen2.5:7b
```

### Connect to vLLM (OpenAI-Compatible)

```bash
-e INFERENCE_PROVIDER=openai_compatible \
-e INFERENCE_BASE_URL=http://host.docker.internal:8000/v1/chat/completions \
-e MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
```

### Connect to LM Studio

```bash
-e INFERENCE_PROVIDER=openai_compatible \
-e INFERENCE_BASE_URL=http://host.docker.internal:1234/v1/chat/completions
```

---

## 🐳 Full Multi-Container Stack (Self-Contained)

If you don't have Ollama installed and want the complete turnkey stack including monitoring and autonomous engines:

```bash
git clone https://github.com/Zyrabit-tech/zyrabit-SLM.git
cd zyrabit-SLM
./zyra.sh install
```

### Available Docker Compose Profiles

* `--profile production` — Traefik TLS proxy with rate limiting and secure headers.
* `--profile tenstorrent` — Hardware acceleration for Tenstorrent Blackhole & Wormhole NPUs.
* `--profile db` — PostgreSQL with pgvector for high-concurrency production deployments.
* `--profile automation` — n8n webhook workflow automation bridge.

---

## 🏥 Health Check & Verification

Once your container is running, verify health via CLI:

```bash
# API & Engine Health
curl http://localhost:8080/v1/health

# Test Chat Query with PII Masking
curl -X POST http://localhost:8080/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello Zyrabit! My email is test@company.com"}'
```

---

## 📚 Community, Documentation & Commercial Support

* **Documentation Portal:** [https://docs.zyrabit.com](https://docs.zyrabit.com)
* **GitHub Repository:** [https://github.com/Zyrabit-tech/zyrabit-SLM](https://github.com/Zyrabit-tech/zyrabit-SLM)
* **Official Website:** [https://zyrabit.com](https://zyrabit.com)
* **Turnkey Hardware Appliances & Enterprise SLA:** Need an air-gapped tactical field kit or rackmount appliance preloaded with calibrated weights for your hospital, newsroom, or enterprise? Contact `contact@zyrabit.com`.

---

**License:** MIT Open Source License. © 2026 Zyrabit. Enterprise Privacy, Local Intelligence.
