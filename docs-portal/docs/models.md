# Model Configuration

Zyrabit SLM uses **Ollama** as its core inference engine. This allows you to run state-of-the-art small language models (SLMs) locally with high performance.

## Default Model
By default, Zyrabit uses **Qwen 2.5 (7B or 1.5B)** depending on your detected system RAM:
- **< 12GB RAM:** Qwen 2.5 (1.5B) - Optimized for low resources.
- **>= 12GB RAM:** Qwen 2.5 (7B) - Balanced performance and quality.

## Changing Models

You can override the default model using the `--model` flag in the setup script:

```bash
./zyra-up.sh install --model mistral
```

Or by setting the `MODEL_NAME` environment variable in `zyrabit-slm/.env`:

```env
MODEL_NAME="llama3"
```

---

## Supported Models

Since Zyrabit uses Ollama, you can use any model from the [Ollama Library](https://ollama.com/library). Popular choices include:
- `llama3`: Meta's latest general-purpose model.
- `mistral`: High-efficiency 7B model.
- `codellama`: Specialized for programming tasks.
- `phi3`: Microsoft's ultra-small but capable model.

To pull a new model manually:
```bash
docker exec -it zyrabit-engine ollama pull <model_name>
```

---

## Hardware Acceleration

Zyrabit automatically detects and configures the best acceleration backend:

### 🚀 NVIDIA GPU (CUDA)
If an NVIDIA GPU is detected, the `zyrabit-engine` will use the GPU for all inference tasks. Ensure the **NVIDIA Container Toolkit** is installed on the host.

### 🍎 Apple Silicon (Metal)
On Mac, Zyrabit utilizes the unified memory architecture and Metal API for high-speed inference.

### ⚙️ CPU Only
If no GPU is found, the engine falls back to CPU inference. We recommend using smaller quantized models (e.g., 1.5B or 3B) for a smooth experience.

---

## Embedding Models

For RAG (Retrieval-Augmented Generation), Zyrabit uses a separate embedding model to vectorize documents. By default, it uses:
- `mxbai-embed-large`: A high-performance embedding model.

You can change this in the API configuration if needed, but the default is recommended for most use cases.
