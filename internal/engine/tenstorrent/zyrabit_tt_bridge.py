#!/usr/bin/env python3
"""Zyrabit Tenstorrent bridge.

The bridge exposes a small inference-compatible surface for validating Qwen
2.5 7B-Instruct through Tenstorrent's compiler stack when available. It is
designed to remain useful in air-gapped and low-memory Docker environments by
falling back to a deterministic mock backend instead of crashing the service.
"""

import argparse
import hashlib
import importlib
import json
import logging
import os
import platform
import resource
import sys
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Protocol


LOGGER = logging.getLogger("zyrabit.tt.bridge")

DEFAULT_MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_WORMHOLE_CLOCK_HZ = 1_200_000_000
DEFAULT_MIN_RAM_GB = 24.0


class BackendMode(str, Enum):
    AUTO = "auto"
    MOCK = "mock"
    TT_SIM = "tt-sim"


@dataclass(frozen=True)
class BridgeConfig:
    model_id: str
    mode: BackendMode
    host: str
    port: int
    max_new_tokens: int
    wormhole_clock_hz: int
    min_ram_gb: float
    allow_remote_model: bool

    @classmethod
    def from_env(cls) -> "BridgeConfig":
        return cls(
            model_id=os.getenv("ZYRABIT_TT_MODEL_ID", DEFAULT_MODEL_ID),
            mode=BackendMode(os.getenv("ZYRABIT_TT_MODE", BackendMode.AUTO.value)),
            host=os.getenv("ZYRABIT_TT_HOST", "0.0.0.0"),
            port=int(os.getenv("ZYRABIT_TT_PORT", "8090")),
            max_new_tokens=int(os.getenv("ZYRABIT_TT_MAX_NEW_TOKENS", "128")),
            wormhole_clock_hz=int(
                os.getenv("ZYRABIT_TT_WORMHOLE_CLOCK_HZ", str(DEFAULT_WORMHOLE_CLOCK_HZ))
            ),
            min_ram_gb=float(os.getenv("ZYRABIT_TT_MIN_RAM_GB", str(DEFAULT_MIN_RAM_GB))),
            allow_remote_model=os.getenv("ZYRABIT_TT_ALLOW_REMOTE_MODEL", "false").lower()
            in {"1", "true", "yes"},
        )


@dataclass(frozen=True)
class CompilerMetrics:
    estimated_cycles_per_token: int
    sram_utilization_pct: float
    dram_utilization_pct: float
    total_compiled_ops: int
    fused_ops: int
    sharded_ops: int
    projected_tokens_per_second_n300: float
    compiler: str
    backend: str
    source: str


@dataclass(frozen=True)
class InferenceResult:
    response: str
    metrics: CompilerMetrics
    model_id: str
    mode: str
    elapsed_ms: float


class InferenceBackend(Protocol):
    def generate(self, prompt: str, max_new_tokens: int) -> InferenceResult:
        ...

    def health(self) -> Dict[str, Any]:
        ...


def _physical_ram_gb() -> float:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return (pages * page_size) / (1024**3)
    except (AttributeError, OSError, ValueError):
        pass

    if platform.system() == "Darwin":
        try:
            import subprocess

            out = subprocess.check_output(
                ["sysctl", "-n", "hw.memsize"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            return int(out) / (1024**3)
        except Exception:
            return 0.0
    return 0.0


def _rss_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return usage / (1024**2)
    return usage / 1024


def _require_module(name: str) -> Any:
    return importlib.import_module(name)


def _project_tokens_per_second(clock_hz: int, cycles_per_token: int) -> float:
    if cycles_per_token <= 0:
        return 0.0
    return round(clock_hz / cycles_per_token, 2)


def _mock_metrics(prompt: str, config: BridgeConfig, reason: str) -> CompilerMetrics:
    digest = hashlib.sha256(f"{config.model_id}:{prompt}".encode("utf-8")).digest()
    jitter = int.from_bytes(digest[:2], "big") % 90_000
    cycles = 1_840_000 + jitter
    fused_ops = 1_168 + digest[2] % 64
    sharded_ops = 192 + digest[3] % 24
    return CompilerMetrics(
        estimated_cycles_per_token=cycles,
        sram_utilization_pct=round(67.5 + (digest[4] % 80) / 10, 2),
        dram_utilization_pct=round(28.0 + (digest[5] % 65) / 10, 2),
        total_compiled_ops=fused_ops + sharded_ops + 2_436,
        fused_ops=fused_ops,
        sharded_ops=sharded_ops,
        projected_tokens_per_second_n300=_project_tokens_per_second(
            config.wormhole_clock_hz, cycles
        ),
        compiler="tt-forge/tt-mlir",
        backend="software-simulation-golden",
        source=f"mock:{reason}",
    )


class MockTenstorrentBackend:
    def __init__(self, config: BridgeConfig, reason: str = "forced") -> None:
        self._config = config
        self._reason = reason

    def generate(self, prompt: str, max_new_tokens: int) -> InferenceResult:
        started = time.perf_counter()
        metrics = _mock_metrics(prompt, self._config, self._reason)
        clipped = " ".join(prompt.strip().split())[:240]
        response = (
            "Zyrabit-TT-Bridge mock simulation completed. "
            f"Model={self._config.model_id}; prompt_digest="
            f"{hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:12]}; "
            f"summary='{clipped or 'empty prompt'}'."
        )
        return InferenceResult(
            response=response[: max(64, max_new_tokens * 8)],
            metrics=metrics,
            model_id=self._config.model_id,
            mode=BackendMode.MOCK.value,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    def health(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "mode": BackendMode.MOCK.value,
            "reason": self._reason,
            "model_id": self._config.model_id,
            "rss_mb": round(_rss_mb(), 2),
            "ram_gb": round(_physical_ram_gb(), 2),
        }


class TenstorrentSimulationBackend:
    """Thin adapter around Tenstorrent Python packages.

    Tenstorrent package APIs are still moving. This adapter intentionally keeps
    all TT-specific calls behind one class so production hardware dispatch can
    replace only this layer when the DevKit arrives.
    """

    def __init__(self, config: BridgeConfig) -> None:
        self._config = config
        self._torch = _require_module("torch")
        self._torch_xla = _require_module("torch_xla")
        self._tt_torch = _require_module("tt_torch")
        self._tt_forge = _require_module("tt_forge")
        self._transformers = _require_module("transformers")
        self._compiled: Optional[Any] = None
        self._tokenizer: Optional[Any] = None

    def _load_model(self) -> Any:
        if self._compiled is not None:
            return self._compiled

        local_files_only = not self._config.allow_remote_model
        tokenizer = self._transformers.AutoTokenizer.from_pretrained(
            self._config.model_id,
            local_files_only=local_files_only,
            trust_remote_code=False,
        )
        model = self._transformers.AutoModelForCausalLM.from_pretrained(
            self._config.model_id,
            torch_dtype=getattr(self._torch, "bfloat16", None),
            low_cpu_mem_usage=True,
            local_files_only=local_files_only,
            trust_remote_code=False,
        )
        model.eval()

        compile_kwargs: Dict[str, Any] = {
            "backend": "tt",
            "device": "tt",
            "enable_golden": True,
        }

        # Prefer explicit TT wrappers when present, but avoid binding to a
        # single release of tt_torch/tt_forge.
        if hasattr(self._tt_torch, "compile"):
            compiled = self._tt_torch.compile(model, **compile_kwargs)
        elif hasattr(self._tt_forge, "compile"):
            compiled = self._tt_forge.compile(model, **compile_kwargs)
        else:
            raise RuntimeError("No supported compile() entrypoint found in tt_torch/tt_forge")

        self._tokenizer = tokenizer
        self._compiled = compiled
        return compiled

    def _extract_metrics(self, compiled: Any) -> Mapping[str, Any]:
        candidates = ("metrics", "compile_metrics", "get_metrics", "statistics")
        for name in candidates:
            attr = getattr(compiled, name, None)
            if attr is None:
                continue
            data = attr() if callable(attr) else attr
            if isinstance(data, Mapping):
                return data
        return {}

    def generate(self, prompt: str, max_new_tokens: int) -> InferenceResult:
        started = time.perf_counter()
        compiled = self._load_model()
        tokenizer = self._tokenizer
        if tokenizer is None:
            raise RuntimeError("Tokenizer was not initialized")

        tokens = tokenizer(prompt, return_tensors="pt")
        if hasattr(compiled, "generate"):
            output = compiled.generate(**tokens, max_new_tokens=max_new_tokens)
        else:
            with self._torch.no_grad():
                output = compiled(**tokens)
        response = tokenizer.decode(output[0], skip_special_tokens=True)
        raw_metrics = dict(self._extract_metrics(compiled))
        cycles = int(raw_metrics.get("estimated_cycles_per_token", 1_840_000))
        fused_ops = int(raw_metrics.get("fused_ops", raw_metrics.get("fusions", 0)))
        sharded_ops = int(raw_metrics.get("sharded_ops", raw_metrics.get("sharding", 0)))
        metrics = CompilerMetrics(
            estimated_cycles_per_token=cycles,
            sram_utilization_pct=float(raw_metrics.get("sram_utilization_pct", 0.0)),
            dram_utilization_pct=float(raw_metrics.get("dram_utilization_pct", 0.0)),
            total_compiled_ops=int(raw_metrics.get("total_compiled_ops", 0)),
            fused_ops=fused_ops,
            sharded_ops=sharded_ops,
            projected_tokens_per_second_n300=_project_tokens_per_second(
                self._config.wormhole_clock_hz, cycles
            ),
            compiler="tt-forge/tt-mlir",
            backend="software-simulation-golden",
            source="tt-simulation",
        )
        return InferenceResult(
            response=response,
            metrics=metrics,
            model_id=self._config.model_id,
            mode=BackendMode.TT_SIM.value,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    def health(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "mode": BackendMode.TT_SIM.value,
            "model_id": self._config.model_id,
            "rss_mb": round(_rss_mb(), 2),
            "ram_gb": round(_physical_ram_gb(), 2),
            "torch_xla": getattr(self._torch_xla, "__version__", "unknown"),
        }


class BackendFactory:
    @staticmethod
    def create(config: BridgeConfig) -> InferenceBackend:
        ram_gb = _physical_ram_gb()
        if config.mode == BackendMode.MOCK:
            return MockTenstorrentBackend(config, "forced")
        if ram_gb and ram_gb < config.min_ram_gb:
            if config.mode == BackendMode.TT_SIM:
                raise RuntimeError(
                    f"Refusing TT simulation with {ram_gb:.2f}GB RAM; "
                    f"minimum is {config.min_ram_gb:.2f}GB"
                )
            return MockTenstorrentBackend(config, "insufficient-ram")
        try:
            return TenstorrentSimulationBackend(config)
        except Exception as exc:
            if config.mode == BackendMode.TT_SIM:
                raise
            LOGGER.warning("TT simulation unavailable, using mock mode: %s", exc)
            return MockTenstorrentBackend(config, f"tt-unavailable:{exc.__class__.__name__}")


def _result_to_dict(result: InferenceResult) -> Dict[str, Any]:
    payload = asdict(result)
    payload["metrics"] = asdict(result.metrics)
    return payload


def run_cli(args: argparse.Namespace) -> int:
    config = BridgeConfig.from_env()
    if args.mode:
        config = BridgeConfig(
            model_id=args.model_id or config.model_id,
            mode=BackendMode(args.mode),
            host=config.host,
            port=config.port,
            max_new_tokens=args.max_new_tokens,
            wormhole_clock_hz=config.wormhole_clock_hz,
            min_ram_gb=config.min_ram_gb,
            allow_remote_model=config.allow_remote_model,
        )
    backend = BackendFactory.create(config)
    result = backend.generate(args.prompt, args.max_new_tokens)
    print(json.dumps(_result_to_dict(result), ensure_ascii=False, indent=2))
    return 0


def run_server(config: BridgeConfig) -> None:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
    import uvicorn

    class GenerateRequest(BaseModel):
        prompt: str = Field(min_length=1, max_length=32_768)
        max_new_tokens: int = Field(default=config.max_new_tokens, ge=1, le=2_048)

    app = FastAPI(
        title="Zyrabit-TT-Bridge",
        version="0.1.0",
        description="Tenstorrent TT-MLIR simulation bridge for sovereign inference validation.",
    )
    backend = BackendFactory.create(config)

    @app.get("/v1/health")
    def health() -> Dict[str, Any]:
        return backend.health()

    @app.post("/v1/generate")
    def generate(request: GenerateRequest) -> Dict[str, Any]:
        try:
            return _result_to_dict(
                backend.generate(request.prompt, request.max_new_tokens)
            )
        except Exception as exc:
            LOGGER.exception("Generation failed")
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    uvicorn.run(app, host=config.host, port=config.port, log_level="info")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Zyrabit Tenstorrent simulation bridge")
    subcommands = parser.add_subparsers(dest="command")

    serve = subcommands.add_parser("serve", help="Run FastAPI bridge")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)

    infer = subcommands.add_parser("infer", help="Run one inference request")
    infer.add_argument("prompt")
    infer.add_argument("--max-new-tokens", type=int, default=128)
    infer.add_argument("--model-id", default=None)
    infer.add_argument("--mode", choices=[mode.value for mode in BackendMode], default=None)

    parser.set_defaults(command="serve")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(
        level=os.getenv("ZYRABIT_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = parse_args(argv)
    if args.command == "infer":
        return run_cli(args)

    config = BridgeConfig.from_env()
    if getattr(args, "host", None):
        config = BridgeConfig(
            model_id=config.model_id,
            mode=config.mode,
            host=args.host,
            port=config.port,
            max_new_tokens=config.max_new_tokens,
            wormhole_clock_hz=config.wormhole_clock_hz,
            min_ram_gb=config.min_ram_gb,
            allow_remote_model=config.allow_remote_model,
        )
    if getattr(args, "port", None):
        config = BridgeConfig(
            model_id=config.model_id,
            mode=config.mode,
            host=config.host,
            port=args.port,
            max_new_tokens=config.max_new_tokens,
            wormhole_clock_hz=config.wormhole_clock_hz,
            min_ram_gb=config.min_ram_gb,
            allow_remote_model=config.allow_remote_model,
        )
    run_server(config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
