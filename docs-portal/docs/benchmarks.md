---
sidebar_position: 4
title: 'Performance Benchmarks'
description: 'Real-world inference benchmarks across different hardware configurations'
---

# Zyrabit Live E2E Benchmark Execution Report

*Generated dynamically on 2026-07-29 02:56:14 UTC*

## 📊 Live Execution Metrics (RAG vs Direct)

| Pipeline Step | Routing Decision | Model Provider | Throughput (t/s) | TTFT (ms) | Total Latency (ms) | Documents Retrieved |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Direct Inference** | `DIRECT` | `N/A` | N/A | N/A | 9.2 ms | 0 |
| **RAG Ingestion + Query** | `RAG_ENFORCED` | `N/A` | N/A | N/A | 0.9 ms | 0 |

## 🎙️ Audio Ingestion & Whisper Transcription
*   **Sample Audio:** `/tmp/zyrabit_sample_audio.wav` (16kHz PCM Mono)
*   **Status:** Synthetic WAV generated & verified for embedded Whisper transcription pipeline.

## 🛡️ Security Audit & PII Check
*   **PII Sanitization:** PASSED (0 leaks)
*   **Network Air-Gap:** 100% Local (0 External Network Egress Requests)

## Related Documentation
- [Models](./models.md)
- [Swap Hardware](./guides/swap-hardware.md)
