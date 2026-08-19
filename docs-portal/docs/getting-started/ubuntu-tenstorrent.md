---
sidebar_position: 2
title: 'Ubuntu + Tenstorrent P150A'
description: 'Deploy Zyrabit SLM on Ubuntu Linux with a Tenstorrent P150A PCIe accelerator'
---

# Installation Guide: Ubuntu + Tenstorrent P150A (Wormhole)

This guide details the steps to deploy **Zyrabit SLM** on a machine with **Ubuntu Linux** operating system equipped with the **Tenstorrent P150A** AI accelerator card (Wormhole PCIe RISC-V architecture).

---

## 📋 System Prerequisites

### 1. Hardware Requirements

- **Processor:** x86_64 or ARM64 (minimum 4 cores)
- **Host RAM:** 16 GB or higher (24 GB recommended if running 7B models)
- **PCIe Accelerator:** **Tenstorrent P150A** card (16 GB TT-DDR6) installed in a PCIe Gen4/Gen5 slot with 8-pin auxiliary power.
- **PCIe Slot:** Verify access to the `/dev/tenstorrent` device.

### 2. Software Requirements (Ubuntu 22.04 LTS or 24.04 LTS)

- Ubuntu Linux 22.04 LTS or higher (64-bit / x86_64).
- Tenstorrent KMD drivers (`tenstorrent-kmd`) installed.
- Docker Engine & Docker Compose V2.
- Python tool `uv` (for hermetic isolation).

> [!NOTE]
> **If you are on Windows (PowerShell/CMD):**
> `uname` is a Linux command. To verify your processor architecture from Windows before installing Ubuntu:
>
> ```powershell
> (Get-CimInstance Win32_OperatingSystem).OSArchitecture
> # or by running:
> $env:PROCESSOR_ARCHITECTURE
> ```
>
> If it returns `64-bit` or `AMD64`, your machine supports 64-bit Ubuntu for the P150A.

---

## 🛠️ Step 1: Tenstorrent P150A Card Verification

Ensure that Ubuntu recognizes the PCIe card and that the KMD drivers are loaded:

```bash
# 1. Verify presence of the card on the PCIe bus (ID 1e52:f000 or similar)
lspci | grep -i tenstorrent

# 2. Confirm existence of the PCIe device node
ls -l /dev/tenstorrent*

# 3. Verify card status and temperature via tt-smi (if installed)
tt-smi
```

> [!IMPORTANT]
> If the `/dev/tenstorrent` device does not exist, install the official Tenstorrent kernel driver by running:
>
> ```bash
> sudo apt-get update && sudo apt-get install -y dkms build-essential
> git clone https://github.com/tenstorrent/tt-kmd.git
> cd tt-kmd && sudo make install
> sudo modprobe tenstorrent
> ```

---

## 🚀 Step 2: Clone the Zyrabit SLM Repository

```bash
# Clone the project
git clone https://github.com/Zyrabit-tech/zyrabit-SLM.git
cd zyrabit-SLM
```

---

## ⚡ Step 3: Interactive Installation (Tenstorrent P150A Mode)

Zyrabit includes native support for Tenstorrent accelerators in its unified `./zyra.sh` script:

```bash
# Start the installer
./zyra.sh install
```

In the interactive menu, select your preferred settings:

1. **Hardware / Inference Engine:** Select **`2) Tenstorrent Hardware (vLLM-TT Metalium)`** or accept auto-detection.
2. **AI Model:** Select the desired model (e.g., `qwen2.5:3b`, `deepseek-r1:1.5b`, or `qwen2.5:7b`).
3. **ReAct Agent:** Select `1) Yes` to enable reasoning + tools.
4. **Deployment Mode:** `1) Full Sovereign Platform` or `2) Standalone Bare Engine`.

### Direct Installation without Prompts (Via Flags / Variables)

If you prefer to perform the automated installation from the terminal or CI/CD scripts:

```bash
# Silent install using existing .env or default flags
./zyra.sh install -y
```

---

## 🐋 Step 4: Tenstorrent Container Architecture

When the `tenstorrent` profile is selected, Docker Compose brings up the **`zyrabit-tt-metal`** service defined in `docker-compose.yml`:

```yaml
  zyrabit-tt-metal:
    image: zyrabit-slm/tt-bridge
    container_name: zyrabit-tt-metal
    profiles: [ "tenstorrent" ]
    devices:
      - /dev/tenstorrent:/dev/tenstorrent
    ipc: host
    environment:
      - ZYRABIT_TT_MODE=metal
      - ZYRABIT_TT_MODEL_ID=Qwen/Qwen2.5-7B-Instruct
    ports:
      - "8090:8090"
```

This service:

- Directly mounts the `/dev/tenstorrent` hardware device inside the Linux container.
- Uses the TT-MLIR / TT-Metalium compilation to run matrix inference on the P150A's RISC-V Tensix cores.
- Exposes the OpenAI-compatible API on local port `8090`.

---

## ✅ Step 5: Health Check and Testing

Once the stack is deployed, verify the connectivity and the accelerator status:

```bash
# 1. Check containers status
./zyra verify

# 2. Query the activated inference endpoint
curl http://localhost:8082/v1/health

# 3. Perform a test query to the Zyrabit API
curl -X POST http://localhost:8082/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer zyrabit-local-token" \
  -d '{"text": "Hello Zyrabit, confirm that you are running inference on the Tenstorrent P150A card."}'
```

---

## 📊 Step 6: Performance Benchmarks

To measure tokens per second (t/s) and time to first token (TTFT) on the P150A:

```bash
# Run live benchmark
./zyra benchmark
```

The results will reflect the hardware acceleration on the Tenstorrent card without CPU or host RAM consumption.
