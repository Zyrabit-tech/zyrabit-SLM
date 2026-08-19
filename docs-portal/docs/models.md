---
sidebar_position: 4
title: Model Configuration
description: "Supported inference providers, model selection by hardware, and embedding configuration."
---

# Model Configuration

Zyrabit SLM utilizes **Ollama** as the core inference engine, enabling the local execution of Small Language Models (SLMs) with high performance and low latency.

## Default Model Configuration

The stack selects a default model based on detected system resources during initialization:

- **< 12GB RAM:** Qwen 2.5 (1.5B) - Optimized for resource-constrained environments.
- **>= 12GB RAM:** Qwen 2.5 (7B) - Balanced for accuracy and throughput.

## Overriding Defaults

Users can specify an alternative model during installation using the `--model` flag:

```bash
./zyra.sh install --model mistral
```

Alternatively, the `MODEL_NAME` environment variable can be set in the `.env` file:

```env
MODEL_NAME="llama3"
```

## Model Selection Matrix & Architectural Archetypes

Zyrabit SLM is designed to be completely model-agnostic, supporting three distinct model archetypes depending on your enterprise workload:

| Archetype / Profile | Recommended Models | Primary Strengths | Ideal Enterprise Workload |
| :--- | :--- | :--- | :--- |
| 💬 **Instruct-Tuned SLM** | `Qwen 2.5 (3B / 7B)`, `Llama 3.2 (3B)` | Ultra-low TTFT (<150ms), natural conversational flow, zero token waste | Interactive Web Chat, fast document Q&A, executive summaries |
| 🧠 **Reasoning (CoT) SLM** | `DeepSeek-R1-Distill (1.5B / 7B / 14B)` | Multi-step scratchpad (`<think>`), logic self-verification | Complex contract audit, financial reconciliation, multi-hop reasoning |
| 🛠️ **Autonomous Agent / Coder** | `Qwen 2.5 Coder (7B)`, `Hermes 3 (8B)` | Deterministic JSON output, strict MCP schema compliance | Automated tool invocation, database migrations, ERP connectors |

---

## Model-Agnostic UI: `<think>` Accordion Support

Reasoning models (like `DeepSeek-R1`) spend internal tokens generating chain-of-thought scratchpad text enclosed in `<think>...</think>` tags before emitting their final answer.

Zyrabit SLM features built-in model-agnostic frontend parsing:
1. **Automatic Detection:** Any tokens within `<think>...</think>` are automatically parsed and isolated into a collapsible **`🧠 Proceso de Razonamiento (Pensamiento)`** UI accordion.
2. **Clean Output:** The primary chat bubble displays only the verified, grounded response with evidence citations.
3. **Token Allocation:** When using Reasoning models, ensure `INFERENCE_TIMEOUT_SECONDS=120` or higher to accommodate multi-step verification.

---

## Hardware Acceleration & Providers

Zyrabit automatically discovers host accelerators and routes inference to the optimal backend:

### Tenstorrent Blackhole (vLLM-TT Metalium)
Native PCIe NPU execution using Tensix compute cores. Pre-compiled model specifications are available in `app/infrastructure/engine/tenstorrent/`.

### Apple Silicon (Metal / MLX)
Unified memory acceleration leveraging macOS Metal performance shaders.

### NVIDIA GPU (CUDA / TensorRT-LLM)
High-throughput batching and fp16/int8 execution via NVIDIA Container Toolkit.

### Multi-Core x86 CPU (AVX2 / llama.cpp)
Low-footprint local execution using quantized GGUF weights. Recommended for edge devices and lightweight 1.5B - 3B models.

---

## Embedding Models for Hybrid RAG

For document vectorization, Zyrabit isolates generation from retrieval:
- **Default:** `mxbai-embed-large` / `nomic-embed-text`
- **Lexical Index:** SQLite FTS5 with BM25 scoring for deterministic exact keyword matching.
