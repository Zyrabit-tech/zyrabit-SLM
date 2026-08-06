---
sidebar_position: 1
---

# Quickstart Fundamentals

The deployment of Zyrabit SLM requires technical precision and environmental isolation. This guide provides a step-by-step procedure to initialize your environment and launch the core services.

Zyrabit adopts a **Zero-Config Bias**: The engine automatically detects and utilizes the optimal compute kernels (Metal, CUDA, or AVX2) based on your host hardware.

---

## 1. Environment Preparation

Before executing the orchestration, ensure your *Standard Toolchain* is configured. We utilize `uv` for hermetic dependency management and Docker for container isolation.

### Install the `uv` Toolchain
`uv` ensures that Python dependencies remain isolated and reproducible.

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

<Tabs groupId="operating-systems">
  <TabItem value="mac" label="macOS / Linux" default>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

  </TabItem>
  <TabItem value="wsl" label="Windows (WSL2)">

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

  </TabItem>
</Tabs>

### Verify Docker Status
Ensure Docker is running on your host system.

```bash
docker info
```

---

## 2. Project Initialization

Follow these steps to clone the repository and prepare the local environment.

### Step 1: Clone the Repository
Download the Zyrabit SLM source code to your local machine.

```bash
git clone https://github.com/Zyrabit-tech/zyrabit-SLM.git
```

### Step 2: Navigate to Project Root
Change your working directory to the repository folder.

```bash
cd zyrabit-SLM
```

### Step 3: Initialize the Virtual Environment
Create a hermetic environment using `uv` to manage orchestration dependencies.

```bash
uv venv
```

### Step 4: Activate the Environment
Load the isolated environment into your current shell session.

```bash
source .venv/bin/activate
```

### Step 5: Sync Dependencies
Install the required Python packages defined in the project.

```bash
uv pip install -r requirements.txt
```

---

## 3. Launching the Stack

Zyrabit uses a unified CLI script (`zyra.sh`) that automatically chooses the best configuration for your hardware. **Local/Dev mode is the default — no extra flags required.**

### First-Time Installation (Local / Dev Mode)

```bash
./zyra.sh install
```

This single command:
1. Detects your hardware (RAM, GPU, Apple Silicon Metal)
2. Creates `.env` from `example.env` if it doesn't exist
3. Builds Docker images for the API, Web UI, MCP, and ChromaDB
4. Starts all containers on local ports (`8082` API · `3000` Web UI · `3001` Grafana)
5. Pulls the best-fit SLM model based on your available RAM

### Interactive Setup Wizard

For a guided configuration (model selection, inference engine, PostgreSQL, Whisper audio):

```bash
./zyra.sh wizard
```

### Access Your Services

| Service | URL |
|---|---|
| **Web UI** | http://localhost:3000 |
| **API** | http://localhost:8082/v1 |
| **Health** | http://localhost:8082/v1/health |
| **Grafana** | http://localhost:3001 |
| **ChromaDB** | http://localhost:8000 |

### Verify Health

```bash
./zyra.sh verify
```

> [!TIP]
> On the first run, the system will download approximately 3GB of container images and the foundational SLM model. Once running, test with: `curl http://localhost:8082/v1/health`

---

## 4. Going to Production

When ready to deploy with a domain, HTTPS, and PostgreSQL:

```bash
./zyra.sh install --production
```

This activates:
- **Traefik** reverse proxy with automatic TLS certificates
- **Custom domain** configuration
- **PostgreSQL** as a persistent relational database (via `--profile db`)
- Strict rate limiting and security headers

