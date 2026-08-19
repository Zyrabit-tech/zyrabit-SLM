---
sidebar_position: 2
title: 'Configure Models'
description: 'Guide for multi-model setup including text, audio, and embeddings'
component_type: 'guide'
layer: 'infrastructure'
ports: ['InferencePort', 'StreamingInferencePort']
technologies: ['Ollama', 'MLX', 'OpenAI', 'Whisper']
---

# Configure Models

Zyrabit SLM allows configuring multiple models for text generation, embeddings, and audio transcription.

## Ports Overview

```python
from typing import Protocol, AsyncIterator

class InferencePort(Protocol):
    def generate(self, request: dict) -> dict:
        ...

class StreamingInferencePort(Protocol):
    async def stream_generate(self, request: dict) -> AsyncIterator[str]:
        ...
```

## Creating a New Inference Adapter

To switch to a different provider (e.g., an OpenAI-compatible endpoint):

1. **Create Adapter**: Create `app/infrastructure/inference/openai_adapter.py`.
2. **Implement Interface**: Inherit from `InferencePort` and/or `StreamingInferencePort`.
3. **Configure**: Update `app/inference_factory.py` to return your new adapter when `INFERENCE_PROVIDER=openai`.

> [!TIP]
> You can mix and match providers. For example, use local Ollama for embeddings and cloud Anthropic for chat generation.
