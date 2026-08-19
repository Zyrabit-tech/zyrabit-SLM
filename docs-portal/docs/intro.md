---
sidebar_position: 1
title: Introduction
description: "Zyrabit SLM — A production-grade local AI orchestration stack with pluggable hexagonal architecture for sovereign, offline-capable document analysis and inference."
slug: /
---

# Zyrabit SLM

Zyrabit SLM is a production-grade Small Language Model (SLM) orchestration stack designed for on-premise and private cloud environments. It provides a containerized architecture to deploy, manage, and scale local AI capabilities while maintaining strict data privacy and network isolation.

## 🎥 See it in Action: True Sovereign AI

Curious about what this looks like in practice? We've recorded a hands-on demo showcasing Zyrabit Platform running 100% offline.

Watch the system process voice commands and capture images in real-time without relying on a single external API or internet connection. This is what true local intelligence looks like.

[👉 Watch the Offline Demo Here](https://assets.zyrabit.com/streaming/zyrabit_ocrtex_bot.mp4)

> ℹ️ **Note:** The video audio is in Spanish.

## 🤖 Sovereign Runtime for AI Agents

Zyrabit SLM serves as a **local-first backend and security firewall for autonomous AI agents** (Cursor, Antigravity, AutoGen, CrewAI, LangGraph, and Cline):

- **Zero-Trust Tool Execution (MCP)**: Safely exposes local file operations, databases, and internal APIs to agents via the standard [Model Context Protocol](https://modelcontextprotocol.io).
- **PII & Secret Protection**: Outbound agent prompts are automatically scrubbed of credentials, API keys, and sensitive personally identifiable information before hitting models.
- **Sovereign Agent Memory**: State, conversation history, and document embeddings stay local in SQLite WAL and ChromaDB — zero external data egress.

## Architecture & Design Principles

Zyrabit is built on a zero-trust architecture, ensuring that data processing remains entirely within the host network perimeter. It integrates vector databases, local inference engines, and workflow automation into a unified, reproducible deployment model.

### Core Capabilities

- **Private RAG & Agent Memory:** A high-performance vector retrieval system coupled with local language models for deterministic, context-aware querying of proprietary datasets.
- **Autonomous Agent Tooling (MCP):** Pre-packaged Model Context Protocol servers allowing AI agents to interact with on-premise infrastructure safely.
- **Hardware-Aware Inference:** Dynamic compute routing that automatically maps execution to the optimal available backend (Apple Metal, NVIDIA CUDA, or CPU/AVX2) without manual configuration overhead.
- **Native Observability:** Integrated telemetry stack utilizing Prometheus and Grafana to expose critical metrics, including inference latency, VRAM allocation, and query throughput.
- **Workflow Orchestration:** Native integration with n8n to enable the design and execution of complex, API-driven AI pipelines.

## Target Environments

Zyrabit is engineered for deployments that require stringent data governance and low-latency local execution:
- Sovereign AI Agents operating on corporate codebases and confidential data.
- Air-gapped enterprise networks.
- Compliance-regulated industries (Healthcare, Finance, Public Sector).
- Edge computing nodes and localized data centers.

## Next Steps

To begin deploying the Zyrabit stack, proceed to the [Quickstart Fundamentals](./getting-started/fundamentals.md) guide.
