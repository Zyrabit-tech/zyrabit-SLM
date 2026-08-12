# Validation Roadmap: Zyrabit Local Tenstorrent Bridge

This document defines the testing strategy and protocols for validating the local inference pipeline using Tenstorrent's hardware simulator (Golden Model) for the **Qwen 2.5 1.5B** model.

## 1. Bridge Architecture (`tt-forge` to `tt-mlir`)

The `zyrabit-tt-bridge` execution flow translates dynamic PyTorch computation graphs into executable instructions for Tenstorrent hardware:

1. **Interception & Lowering (StableHLO)**: Using `torch_xla`, we capture the model computation graph and lower it to standard StableHLO intermediate representation.
2. **Compiler Delegation (`tt-forge`)**: Environment is set (`PJRT_DEVICE=TT`) so XLA backend dispatches operations to `tt-forge`, Tenstorrent's compilation framework.
3. **Lowering to `tt-mlir`**: The compiler transforms StableHLO into the specific `tt-mlir` dialect, optimizing tensor placement across the Tensix grid and SRAM (L1) / DRAM allocation.
4. **Simulation (Golden Model)**: With `INFERENCE_PROVIDER=tt-forge-sim`, the final `.tt` binary executes in a CPU emulation layer that models physical silicon timings and behavior.

## 2. Test Protocols

### Test 1: Graph Compilation
- **Goal**: Measure preprocessing / compilation duration to Tenstorrent binaries.
- **Configuration**: `XLA_STABLEHLO_COMPILE=1`, Qwen 2.5 1.5B in `bfloat16`.
- **Metric**: Cold-start time required to generate executable binaries.

### Test 2: Simulator Inference (Golden Model)
- **Goal**: Establish baseline performance (Cycle Counts) expected on physical hardware.
- **Configuration**: Execute inference using `torch_xla.sync(wait=True)` to enforce proper asynchronous barrier measurement.
- **Metric**: Reported cycles per generated token in execution logs.

### Test 3: Data Integrity (Zero-Trust PII Guard)
- **Goal**: Ensure PII obfuscation/masking routines process tensors BEFORE dispatching to simulator/hardware.
- **Configuration**: Test evaluation using a redacted test prompt.
- **Metric**: Verification of clean output without tensor shape corruption or PII leaks in system logs.

## 3. Baseline Reference Metrics (Qwen 2.5 1.5B - bfloat16)

| Metric | Projected Value (TT Simulator) | Notes / Observations |
| :--- | :--- | :--- |
| **Compilation Time** | *[Pending]* s | Duration from XLA graph load to success |
| **SRAM Usage (Est.)** | *[Pending]* MB | On-chip memory required per L1 core |
| **DRAM Usage (Est.)** | *[Pending]* GB | Total memory consumption (bfloat16 weights + KV Cache) |
| **Cycle Counts (Total)** | *[Pending]* | Total clock cycles per forward pass |
| **Latency (Est.)** | *[Pending]* ms/token | Calculated from base frequency of target card |

---
*Note: These benchmarks represent theoretical upper bounds from the Golden Model host environment prior to PCI-Express physical deployment.*
