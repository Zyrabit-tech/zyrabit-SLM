---
sidebar_position: 3
title: Installation
description: Quick install guide for Zyrabit SLM — from clone to running stack in 3 commands.
---

# Installation

## Quick Install

```bash
git clone https://github.com/Zyrabit-tech/zyrabit-SLM.git
cd zyrabit-SLM
chmod +x zyra.sh install.sh
./zyra.sh install
```

> [!TIP]
> **Do not run `./zyra.sh` with `sudo`**:
> Executing the script under `sudo` causes Docker to create root-owned volume files (`chroma-data`, `db_data`, `.env`) that block standard user access.
> If you encounter a Docker `permission denied` error on Linux, configure non-root Docker access instead:
> ```bash
> sudo usermod -aG docker $USER && newgrp docker
> ```

The `install` command will:
1. Detect your hardware (RAM, GPU, Apple Silicon Metal)
2. Create `.env` from `example.env` if it doesn't exist
3. Build Docker images for the API, Web UI, MCP, and ChromaDB
4. Start all containers in local/dev mode with direct open ports
5. Auto-discover local model weights (or pull a model based on available resources)

> [!IMPORTANT]
> **Requirements**: Docker Desktop must be running. A local inference provider (Ollama) will be configured automatically.

## System Requirements

| Component | Minimum | Recommended |
|---|---|---|
| **RAM** | 8 GB | 16+ GB |
| **Disk** | 10 GB free | 20+ GB free |
| **Docker** | Docker Desktop or Engine | Latest stable |
| **OS** | macOS, Linux, WSL2 | macOS (Apple Silicon) or Linux (NVIDIA GPU) |

## Verify Installation

After `zyra.sh install` completes:

```bash
./zyra.sh verify
```

Then open the Web UI at **http://localhost:8080**.

Test the API directly:

```bash
curl http://localhost:8080/v1/health
```

## Next Steps

For a detailed walkthrough including environment setup, `uv` toolchain installation, and production deployment, see the [Quickstart Fundamentals](./getting-started/fundamentals.md) guide.
