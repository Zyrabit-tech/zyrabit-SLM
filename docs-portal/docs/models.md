---
sidebar_position: 1
title: Model Configuration
description: Configure inference models, hardware acceleration backends, and embedding models in Zyrabit SLM.
---

# Model Configuration

Zyrabit SLM uses **Ollama** as the core inference engine, enabling local execution of language models with hardware-aware acceleration. The system automatically selects the optimal backend and model size based on detected hardware at startup.

---

## Auto-Selected Model by RAM

The `zyra-up.sh` script detects available RAM during initialization and selects the default model accordingly:

```bash
# From zyra-up.sh — automatic model selection logic
model_name="${OVERRIDE_MODEL:-qwen2.5:7b}"
if [[ "${ram}" -lt 12 ]]; then model_name="qwen2.5:1.5b"; fi
```

| Available RAM | Default Model | Notes |
|---|---|---|
| `< 12 GB` | `qwen2.5:1.5b` | Optimized for resource-constrained environments |
| `≥ 12 GB` | `qwen2.5:7b` | Balanced accuracy and throughput — recommended |

---

## Overriding the Default Model

### At install time (recommended)

Use the `--model` flag with `zyra-up.sh`:

```bash
./zyra-up.sh install --model mistral
./zyra-up.sh install --model llama3.2:3b
./zyra-up.sh install --model phi3
```

### Via environment variable

Set `MODEL_NAME` in your `zyrabit-slm/.env` file:

```env
MODEL_NAME=mistral
```

Restart the API service after changing this value:

```bash
./zyra-up.sh stop
./zyra-up.sh start
```

### Pull a model manually

If the stack is already running, pull additional models directly into the inference engine:

```bash
docker exec -it zyrabit-engine ollama pull mistral
docker exec -it zyrabit-engine ollama pull codellama
docker exec -it zyrabit-engine ollama pull llama3.2:3b
```

List available models at runtime:

```bash
curl http://localhost:8082/v1/models \
  -H 'Authorization: Bearer zyrabit-local-token'
```

---

## Supported Models

Zyrabit is compatible with any model available in the [Ollama Library](https://ollama.com/library). Common production choices:

| Model | Size | Best for |
|---|---|---|
| `qwen2.5:7b` | ~4.7 GB | Default — general purpose, strong multilingual |
| `qwen2.5:1.5b` | ~1.0 GB | Low-RAM environments, fast TTFT |
| `mistral` | ~4.1 GB | General reasoning, efficient |
| `llama3.2:3b` | ~2.0 GB | Balanced — good for RAG tasks |
| `codellama` | ~3.8 GB | Code generation and review |
| `phi3` | ~2.3 GB | Lightweight, Microsoft's efficient model |
| `llama3:8b` | ~4.7 GB | Meta's general-purpose model |

:::note OpenAI-Compatible Providers
Zyrabit also supports `openai_compatible` as the `INFERENCE_PROVIDER`. Set `INFERENCE_BASE_URL` and `INFERENCE_API_KEY` in your `.env` to point to any OpenAI-compatible API (e.g., LM Studio, LocalAI):

```env
INFERENCE_PROVIDER=openai_compatible
INFERENCE_BASE_URL=http://localhost:8000/v1/chat/completions
INFERENCE_API_KEY=your-local-key
```
:::

---

## Inference Provider Options

The `INFERENCE_PROVIDER` environment variable controls how the API connects to the model backend:

| Value | Description |
|---|---|
| `ollama` | Default — connects to `zyrabit-engine` Docker container (`http://zyrabit-engine:11434`) |
| `ollama_host` | Connects to Ollama running natively on the host (Mac Metal: `http://host.docker.internal:11434`) |
| `vllm` | Compatible with vLLM engine, `llama.cpp` (`llama-server`), or LM Studio |
| `gemini` | Google Gemini API (requires `GEMINI_API_KEY`) |

### Example 1: Connecting to `llama.cpp` (`llama-server`) or `vLLM`
If you run `llama-server` (the native HTTP server from `llama.cpp`) or a `vLLM` instance on your machine:

```env
INFERENCE_PROVIDER=vllm
SLM_URL=http://host.docker.internal:8080/v1/chat/completions
MODEL_NAME=meta-llama/Llama-3.2-3B-Instruct
```

### Example 2: Connecting to Google Gemini
```env
INFERENCE_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy...
MODEL_NAME=gemini-1.5-flash
```

---

## Hardware Acceleration Backends

The `detect_hardware()` function in `zyra-up.sh` identifies the available accelerator and configures the inference URL accordingly:

### Apple Silicon (Metal)

Detected when: `uname -s == Darwin` and `uname -m == arm64`

Ollama runs natively on the host using the Metal API, leveraging unified memory architecture. The Docker `zyrabit-engine` container is skipped; the API routes to `http://host.docker.internal:11434`.

```bash
# Verify Metal acceleration is active
./zyra-up.sh doctor
# Expected output: ✅ Hardware Profile: METAL (RAM: XGB, Cores: Y)
```

### NVIDIA GPU (CUDA)

Detected when: `nvidia-smi` is available on the host.

Requires the **NVIDIA Container Toolkit** installed on the host system. Ollama inside the `zyrabit-engine` container uses CUDA for inference.

### Tenstorrent Hardware

Detected when: `/dev/tenstorrent` exists or `tt-smi` is available.

Uses the dedicated `zyrabit-tt-bridge` or `zyrabit-tt-metal` service (Docker Compose profiles `tenstorrent-sim` or `tenstorrent`). The inference URL is set to `http://zyrabit-tt-bridge:8000`.

```bash
# Start with Tenstorrent hardware profile
./zyra-up.sh start --profile tenstorrent
```

### CPU Fallback

When no GPU or accelerator is detected, Ollama uses optimized CPU instructions (AVX2). Use quantized models with 1.5B–3B parameters for acceptable latency.

---

## Embedding Model

For Retrieval-Augmented Generation (RAG), Zyrabit uses a dedicated embedding model to vectorize documents into ChromaDB:

```env
# zyrabit-slm/.env
EMBEDDING_MODEL=mxbai-embed-large
RAG_COLLECTION=zyrabit_knowledge
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

| Parameter | Default | Description |
|---|---|---|
| `EMBEDDING_MODEL` | `mxbai-embed-large` | Ollama embedding model for document vectorization |
| `RAG_COLLECTION` | `zyrabit_knowledge` | ChromaDB collection name |
| `CHUNK_SIZE` | `1000` | Characters per document chunk |
| `CHUNK_OVERLAP` | `200` | Character overlap between chunks for context continuity |

The embedding model is pulled automatically on first use. To pre-pull it:

```bash
docker exec -it zyrabit-engine ollama pull mxbai-embed-large
```

---

## Inference Timeout

Configure the maximum time the API waits for a model response:

```env
INFERENCE_TIMEOUT_SECONDS=120
```

Increase this value for larger models or complex RAG queries on CPU-only hardware.
