# Installation Guide

Zyrabit SLM is designed to run locally on your infrastructure. The easiest way to get started is using Docker.

## Prerequisites

Before installing Zyrabit SLM, ensure you have the following requirements:

### Hardware Requirements
- **Mac (Apple Silicon):** M1/M2/M3 (Min 8GB RAM, 16GB recommended).
- **Linux/Windows (NVIDIA GPU):** 8GB+ VRAM recommended for 7B models.
- **CPU Only:** 12GB+ System RAM.

### Software Requirements
- **Docker & Docker Compose:** Required for all platforms.
- **Git:** To clone the repository.

---

## Step 1: Install Docker

### 🍎 macOS
1. Download **Docker Desktop for Mac** (select Apple Silicon or Intel chip).
2. Install the `.dmg` and start Docker Desktop.
3. In Settings > Resources, ensure at least **8GB RAM** is allocated.

### 🪟 Windows
1. Download **Docker Desktop for Windows**.
2. Install and ensure **WSL 2** is enabled.
3. Install the **NVIDIA Container Toolkit** if you plan to use a GPU.

### 🐧 Linux (Ubuntu/Debian)
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install NVIDIA Container Toolkit (Optional for GPU)
# Follow instructions at: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
```

---

## Step 2: Clone and Start

### Quick Start (Automatic)
```bash
git clone https://github.com/Zyrabit-tech/zyrabit-SLM.git
cd zyrabit-SLM
./zyra-up.sh install
```

The `zyra-up.sh` script is the main orchestrator. It will:
1. **Doctor:** Validate your environment (CPU/GPU/RAM).
2. **Setup:** Configure environment variables.
3. **Pull:** Download the required Docker images and SLM models (e.g., Qwen 2.5).

---

## Step 3: Troubleshooting

### Docker Permission Denied
On Linux, if you see permission errors, add your user to the docker group:
```bash
sudo usermod -aG docker $USER
# Log out and log back in
```

### SLM Engine Not Starting
If the `zyrabit-engine` fails to start, verify your hardware acceleration:
- Run `nvidia-smi` (Linux/Windows) to check GPU visibility.
- On Mac, ensure Docker Desktop has permission to access the GPU (Metal).

---

## Optional: Manual Workflow

If you prefer to use Docker Compose directly:
```bash
cd zyrabit-slm
docker compose up -d
```

Enable additional features:
- **Documentation Portal:** `docker compose --profile docs up -d`
- **Automation (n8n):** `docker compose --profile automation up -d`
