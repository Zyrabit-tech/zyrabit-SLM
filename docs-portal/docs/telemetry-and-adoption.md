---
sidebar_position: 5
title: Adoption Telemetry & Privacy
description: How adoption metrics and non-PII telemetry function in Zyrabit Platform
---

# 📊 Adoption Telemetry & Sovereign Privacy

At Zyrabit, we believe critical intelligence infrastructure should be sovereign, transparent, and completely under your control. 

To help our engineering team understand adoption trends, hardware architectures in the field (e.g., Apple Silicon, Tenstorrent NPU, NVIDIA GPUs, AMD64 vs ARM64), and operational stability across diverse operating systems (Linux, macOS, Windows WSL2), Zyrabit Platform includes a **minimalist, privacy-first adoption telemetry heartbeat**.

---

## 🔒 The Zero-PII Guarantee

Our telemetry system enforces the following guarantees:

1. **No User Content**: We never transmit document contents, query prompts, chat history, model responses, embeddings, or file names.
2. **No Personal Identifiers**: We never transmit IP addresses, emails, usernames, machine hostnames, or MAC addresses.
3. **Transparent Local Audit**: Every payload transmitted over the wire is copied locally to `db_data/telemetry_audit.json` so system administrators can inspect exactly what was dispatched.
4. **Air-Gap Tolerant**: If an instance operates completely offline without an internet gateway, heartbeat failures are handled silently without disrupting inference, indexing, or startup.

---

## 📋 Telemetry Payload Schema

Here is an exact representation of the payload generated upon startup:

```json
{
  "instance_id": "8f3b2a1c-9942-4f10-b962-d27b9c9f0e12",
  "project": "zyrabit-platform",
  "version": "2.1.0",
  "os_system": "Linux",
  "os_machine": "x86_64",
  "python_version": "3.12.9",
  "execution_environment": "docker",
  "active_provider": "vllm",
  "active_model": "qwen2.5:7b",
  "retrieval_mode": "hybrid",
  "ocr_enabled": false
}
```

### Destination & Storage
- **Receiving Endpoint**: `https://telemetry.zyrabit.com/v1/heartbeat`
- **Aggregation Engine**: Anonymized metrics are aggregated into Grafana/ClickHouse dashboards for cohort analysis (e.g., total active deployments by OS, growth towards 100K installations, adoption of Tenstorrent NPUs).

---

## 🔕 How to Disable Telemetry

For air-gapped field operations, defense missions, or zero-egress compliance environments, telemetry can be permanently disabled in two ways:

### Method 1: Environment Variable
Add the following line to your `.env` or container environment:
```bash
ZYRABIT_TELEMETRY_DISABLED=true
```

### Method 2: Global Do-Not-Track Standard
Zyrabit respects the universal `DO_NOT_TRACK` convention:
```bash
export DO_NOT_TRACK=1
```

When either variable is detected, the telemetry service immediately ceases all network requests.
