# Model Configuration

Zyrabit SLM utilizes **Ollama** as the core inference engine, enabling the local execution of Small Language Models (SLMs) with high performance and low latency.

## Default Model Configuration

The stack selects a default model based on detected system resources during initialization:

- **< 12GB RAM:** Qwen 2.5 (1.5B) - Optimized for resource-constrained environments.
- **>= 12GB RAM:** Qwen 2.5 (7B) - Balanced for accuracy and throughput.

## Overriding Defaults

Users can specify an alternative model during installation using the `--model` flag:

```bash
./zyra-up.sh install --model mistral
```

Alternatively, the `MODEL_NAME` environment variable can be set in the `.env` file:

```env
MODEL_NAME="llama3"
```

---

## Supported Models

Zyrabit is compatible with models available in the [Ollama Library](https://ollama.com/library). Common choices include:

- `llama3`: Meta's general-purpose model.
- `mistral`: High-efficiency 7B model.
- `codellama`: Optimized for programming and logic tasks.
- `phi3`: Lightweight, capable model from Microsoft.

To manually pull a specific model:
```bash
docker exec -it zyrabit-engine ollama pull <model_name>
```

---

## Hardware Acceleration

Zyrabit automatically configures the optimal acceleration backend based on host hardware:

### NVIDIA GPU (CUDA)
Utilizes NVIDIA GPUs for inference. Requires the **NVIDIA Container Toolkit** on the host.

### Apple Silicon (Metal)
Utilizes the unified memory and Metal API on macOS for accelerated performance.

### CPU Fallback
If no GPU is detected, the engine utilizes optimized CPU instructions. It is recommended to use smaller quantized models (1.5B - 3B) for CPU-only deployments.

---

## Embedding Models

For Retrieval-Augmented Generation (RAG), Zyrabit utilizes a dedicated embedding model for document vectorization. 

- **Default:** `mxbai-embed-large`

This model is selected for its high performance in semantic retrieval tasks. It can be modified in the API configuration if a custom embedding space is required.
