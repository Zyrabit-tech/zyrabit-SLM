# Zyrabit SLM

Zyrabit SLM is a production-grade Small Language Model (SLM) orchestration stack designed for on-premise and private cloud environments. It provides a containerized architecture to deploy, manage, and scale local AI capabilities while maintaining strict data privacy and network isolation.

## Architecture & Design Principles

Zyrabit is built on a zero-trust architecture, ensuring that data processing remains entirely within the host network perimeter. It integrates vector databases, local inference engines, and workflow automation into a unified, reproducible deployment model.

### Core Capabilities

- **Private RAG Engine:** A high-performance vector retrieval system coupled with local language models for deterministic, context-aware querying of proprietary datasets.
- **Hardware-Aware Inference:** Dynamic compute routing that automatically maps execution to the optimal available backend (Apple Metal, NVIDIA CUDA, or CPU/AVX2) without manual configuration overhead.
- **Native Observability:** Integrated telemetry stack utilizing Prometheus and Grafana to expose critical metrics, including inference latency, VRAM allocation, and query throughput.
- **Workflow Orchestration:** Native integration with n8n to enable the design and execution of complex, API-driven AI pipelines.

## Target Environments

Zyrabit is engineered for deployments that require stringent data governance and low-latency local execution:
- Air-gapped enterprise networks.
- Compliance-regulated industries (Healthcare, Finance, Public Sector).
- Edge computing nodes and localized data centers.

## Next Steps

To begin deploying the Zyrabit stack, proceed to the [Quickstart Fundamentals](./getting-started/fundamentals.md) guide.
