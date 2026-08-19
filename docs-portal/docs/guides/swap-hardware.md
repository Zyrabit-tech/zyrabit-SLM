---
sidebar_position: 3
title: 'Hardware Configuration'
description: 'Hardware compatibility and configuration for Apple Silicon, NVIDIA, CPU, and Tenstorrent'
component_type: 'guide'
technologies: ['Apple Silicon', 'NVIDIA', 'CPU', 'Tenstorrent']
---

# Hardware Configuration

Zyrabit auto-detects and optimizes for the host hardware using the `zyra.sh` script.

## Auto-Detection by zyra.sh

The installation script inspects your system and selects the best profile:

- **Apple Silicon**: Uses Metal API for hardware acceleration.
- **NVIDIA GPU**: Enables CUDA if NVIDIA Container Toolkit is present.
- **CPU Fallback**: Uses optimized CPU instructions if no accelerator is found.

## Performance Comparison

| Hardware | Acceleration | Target Model Size | Expected Throughput |
|----------|-------------|-------------------|---------------------|
| M3 Max | Metal | 7B - 14B | ~50+ tokens/s |
| RTX 4090 | CUDA | 7B - 32B | ~70+ tokens/s |
| CPU-only | None | 1.5B - 3B | ~5-15 tokens/s |

> [!IMPORTANT]
> If using CPU fallback, strongly consider using smaller quantized models (less than 3B parameters) for acceptable latency.
