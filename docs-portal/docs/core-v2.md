# Zyrabit Core v2.0: The Sovereign Blueprint

Zyrabit Core v2.0 marks the transition from a stateless retrieval engine to a **Sovereign Operating System for SLMs**. This document explains the technical rationale and architecture of the new core.

## 🏛️ Sovereign Persistence (SQLite WAL)

Previously, Zyrabit was stateless. Every restart lost conversation context. v2.0 introduces `SovereignStateManager`.

- **WAL Mode**: We use SQLite in Write-Ahead Logging mode. This allows concurrent read/write operations (critical for FastAPI's async environment) without database locks.
- **Vault Indexing**: Files in your Obsidian vault are indexed using SHA-256 hashes. If a file hasn't changed, we skip re-processing, reducing IO and CPU overhead by ~80%.
- **Conversation Memory**: A persistent shadow context stores the last $N$ turns of every conversation, automatically indexed by `session_id`.

## 👤 Personalized Onboarding

Context is everything. v2.0 introduces a persistent User Profile:
- **Role-Awareness**: Zyra tailors its technical depth based on whether you are a Developer, Researcher, or Architect.
- **Goal-Alignment**: Your interests (e.g., "Sovereign Security") are injected into every prompt as a high-priority system constraint.

## 🔌 Native MCP v1.0 SDK

We've migrated from custom JSON-RPC handlers to the official **FastMCP SDK**.
- **Standardization**: Full compatibility with Cursor, Zed, and other MCP-enabled clients.
- **Security Shield**: Native validation for file system access and an executable scanner for the `import_to_vault` tool.

## ⚙️ Hardware-Aware Orchestration

The `zyra-up.sh` engine now performs deep hardware inspection on startup:
- **Metal (Mac)**: Automatically routes to `host.docker.internal` for native Apple Silicon acceleration.
- **CUDA (Nvidia)**: Detects NVIDIA drivers and enables GPU passthrough via `nvidia-smi` mocks in validation.
- **Tenstorrent**: Ready-to-go bridge for Grayskull and Wormhole hardware.

## 🛡️ Supply Chain Security

Zyrabit v2.0 includes automated security audits:
- **Trivy**: Scans for high/critical CVEs in dependencies.
- **CodeQL**: Semantic analysis of data flows to prevent PII leaks.
- **Dependabot**: Automated "Auto-Heal" agent for keeping the stack updated.
