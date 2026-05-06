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

Once the environment is initialized, you can start the core infrastructure.

### Start the Base Services
This command launches the API, Vector Database, and Inference Engine in the background.

```bash
docker compose up -d
```

### Monitor Service Health
Verify that the inference engine has initialized and is ready to accept requests.

```bash
docker compose logs -f zyrabit-engine
```

> [!TIP]
> On the first run, the system will download approximately 3GB of container images and the foundational SLM model. A successful startup is confirmed by the log: `[INFO] Server running on port 11434`.
