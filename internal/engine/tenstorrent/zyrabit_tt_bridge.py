#!/usr/bin/env python3
"""Zyrabit Tenstorrent bridge.

The bridge exposes an OpenAI-compatible inference surface for validating
Qwen 2.5 7B-Instruct through Tenstorrent's stack.

Backends
--------
``metal``  Proxies OpenAI requests to a real Tenstorrent engine (vLLM-TT /
           tt-metalium) running upstream, measuring TTFT and throughput from
           the streamed response.
``tt-sim`` Runs Tenstorrent Python packages in-process when available.
``mock``   Deterministic fallback so the service stays useful in air-gapped
           and low-memory environments instead of crashing.
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
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Dict, Mapping, Optional, Protocol

import httpx


LOGGER = logging.getLogger("zyrabit.tt.bridge")

DEFAULT_MODEL_ID = "Qwen/Qwen2.5-3B-Instruct"
DEFAULT_WORMHOLE_CLOCK_HZ = 1_200_000_000
DEFAULT_MIN_RAM_GB = 24.0
DEFAULT_UPSTREAM_URL = "http://localhost:8000"


class BackendMode(str, Enum):
    AUTO = "auto"
    MOCK = "mock"
    TT_SIM = "tt-sim"
    METAL = "metal"


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
    upstream_url: str
    upstream_model: str = ""
    upstream_api_key: Optional[str] = None

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
            upstream_url=os.getenv("ZYRABIT_TT_UPSTREAM_URL", DEFAULT_UPSTREAM_URL).rstrip("/"),
            upstream_model=os.getenv("ZYRABIT_TT_UPSTREAM_MODEL", ""),
            upstream_api_key=os.getenv("ZYRABIT_TT_UPSTREAM_API_KEY", None) or None,
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
    usage: Optional[Dict[str, int]] = None
    ttft_ms: Optional[float] = None
    tps: Optional[float] = None


class InferenceBackend(Protocol):
    def generate(self, prompt: str, max_new_tokens: int) -> InferenceResult:
        pass

    def health(self) -> Dict[str, Any]:
        pass


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

        def _get_val(key: str, default: Any) -> Any:
            val = raw_metrics.get(key)
            return val if val is not None else default

        cycles = int(_get_val("estimated_cycles_per_token", 1_840_000))
        fused_ops = int(_get_val("fused_ops", _get_val("fusions", 0)))
        sharded_ops = int(_get_val("sharded_ops", _get_val("sharding", 0)))

        metrics = CompilerMetrics(
            estimated_cycles_per_token=cycles,
            sram_utilization_pct=float(_get_val("sram_utilization_pct", 0.0)),
            dram_utilization_pct=float(_get_val("dram_utilization_pct", 0.0)),
            total_compiled_ops=int(_get_val("total_compiled_ops", 0)),
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


class TenstorrentMetalBackend:
    """OpenAI-compatible proxy to a real Tenstorrent vLLM engine.

    The bridge forwards chat/completion requests to the upstream engine and
    measures TTFT (time to first token) plus throughput from the streamed
    response so the product can surface real silicon metrics.
    """

    def __init__(self, config: BridgeConfig) -> None:
        self._config = config

    @property
    def upstream_model(self) -> str:
        return self._config.upstream_model or self._config.model_id

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._config.upstream_api_key:
            headers["Authorization"] = f"Bearer {self._config.upstream_api_key}"
        return headers

    def generate(self, prompt: str, max_new_tokens: int) -> InferenceResult:
        started = time.perf_counter()
        payload = {
            "model": self.upstream_model,
            "prompt": prompt,
            "max_tokens": max_new_tokens,
            "stream": False,
        }
        with httpx.Client(timeout=300.0) as client:
            resp = client.post(
                f"{self._config.upstream_url}/v1/completions",
                json=payload,
                headers=self._headers(),
            )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Upstream engine error ({resp.status_code}): {resp.text[:500]}"
            )
        body = resp.json()
        choices = body.get("choices") or []
        text = choices[0].get("text", "") if choices else ""
        usage = body.get("usage") or {}
        comp = usage.get("completion_tokens") or max(1, len(text) // 4) if text else 0
        tps = round(comp / (elapsed_ms / 1000), 2) if comp and elapsed_ms > 0 else None
        metrics = CompilerMetrics(
            estimated_cycles_per_token=0,
            sram_utilization_pct=0.0,
            dram_utilization_pct=0.0,
            total_compiled_ops=0,
            fused_ops=0,
            sharded_ops=0,
            projected_tokens_per_second_n300=tps or 0.0,
            compiler="vllm-tt-metalium",
            backend="blackhole-p150",
            source="tt-metal-vllm",
        )
        return InferenceResult(
            response=text,
            metrics=metrics,
            model_id=self._config.model_id,
            mode=BackendMode.METAL.value,
            elapsed_ms=elapsed_ms,
            usage=usage,
            tps=tps,
        )

    def health(self) -> Dict[str, Any]:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self._config.upstream_url}/health")
        except httpx.RequestError as exc:
            return {
                "ok": False,
                "mode": BackendMode.METAL.value,
                "upstream": self._config.upstream_url,
                "model_id": self._config.model_id,
                "reason": f"upstream-unreachable:{exc.__class__.__name__}",
            }
        if resp.status_code != 200:
            return {
                "ok": False,
                "mode": BackendMode.METAL.value,
                "upstream": self._config.upstream_url,
                "reason": f"upstream-http:{resp.status_code}",
            }
        try:
            status = (resp.json() or {}).get("status", "READY")
        except (json.JSONDecodeError, ValueError):
            return {
                "ok": False,
                "mode": BackendMode.METAL.value,
                "upstream": self._config.upstream_url,
                "reason": f"upstream-body-not-json:status={resp.status_code}",
            }
        return {
            "ok": True,
            "mode": BackendMode.METAL.value,
            "upstream": self._config.upstream_url,
            "model_id": self._config.model_id,
            "status": status,
            "engine": "vllm-tt-metalium",
            "arch": "blackhole",
        }

    async def models(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self._config.upstream_url}/v1/models", headers=self._headers()
                )
        except httpx.RequestError as exc:
            return {
                "object": "list",
                "data": [],
                "zyrabit": {"mode": BackendMode.METAL.value, "error": str(exc)},
            }
        if resp.status_code != 200:
            return {"object": "list", "data": []}
        return resp.json()

    async def _proxy_chat(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Proxy a chat completion, forcing streaming upstream to measure TTFT."""
        client_model = payload.get("model") or self._config.model_id
        upstream_payload = dict(payload)
        upstream_payload["model"] = self.upstream_model
        upstream_payload["stream"] = True

        started = time.perf_counter()
        first_token_at: Optional[float] = None
        content_parts: list[str] = []
        finish_reason: Optional[str] = None
        usage: Dict[str, int] = {}

        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{self._config.upstream_url}/v1/chat/completions",
                json=upstream_payload,
                headers=self._headers(),
            ) as resp:
                if resp.status_code != 200:
                    raw = await resp.aread()
                    return {
                        "error": {
                            "message": raw.decode(errors="replace")[:500],
                            "type": "upstream_error",
                            "code": resp.status_code,
                        }
                    }
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    token = delta.get("content")
                    if token:
                        if first_token_at is None:
                            first_token_at = time.perf_counter()
                        content_parts.append(token)
                    fr = choices[0].get("finish_reason")
                    if fr:
                        finish_reason = fr
                    if chunk.get("usage"):
                        usage = chunk["usage"]

        total_ms = (time.perf_counter() - started) * 1000
        ttft_ms = (first_token_at - started) * 1000 if first_token_at else None
        comp = (usage or {}).get("completion_tokens") or len(content_parts)
        decode_ms = total_ms - (ttft_ms or 0)
        tps = round(comp / (decode_ms / 1000), 2) if comp and decode_ms > 0 else None

        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "model": client_model,
            "created": int(started),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "".join(content_parts)},
                    "finish_reason": finish_reason or "stop",
                }
            ],
            "usage": usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "zyrabit": {
                "mode": BackendMode.METAL.value,
                "source": "tt-metal-vllm",
                "engine": "vllm-tt-metalium",
                "arch": "blackhole",
                "ttft_ms": round(ttft_ms, 2) if ttft_ms is not None else None,
                "tps": tps,
                "total_ms": round(total_ms, 2),
                "upstream_model": self.upstream_model,
            },
        }

    async def _proxy_completions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Proxy a text completion using the upstream chat endpoint for TTFT."""
        client_model = payload.get("model") or self._config.model_id
        prompt = payload.get("prompt", "")
        if isinstance(prompt, list):
            prompt = " ".join(str(p) for p in prompt)
        chat_payload = {
            "model": payload.get("model"),
            "messages": [{"role": "user", "content": prompt}],
            "stream": payload.get("stream", False),
        }
        for key in ("max_tokens", "temperature", "top_p", "top_k", "stop", "seed"):
            if key in payload:
                chat_payload[key] = payload[key]
        result = await self._proxy_chat(chat_payload)
        if "error" in result:
            return result
        content = result["choices"][0]["message"]["content"]
        usage = result.get("usage") or {}
        return {
            "id": f"cmpl-{uuid.uuid4().hex[:12]}",
            "object": "text_completion",
            "model": client_model,
            "created": result.get("created"),
            "choices": [
                {
                    "index": 0,
                    "text": content,
                    "finish_reason": result["choices"][0].get("finish_reason"),
                }
            ],
            "usage": usage,
            "zyrabit": result.get("zyrabit"),
        }


class BackendFactory:
    @staticmethod
    def create(config: BridgeConfig) -> InferenceBackend:
        if config.mode == BackendMode.METAL:
            return TenstorrentMetalBackend(config)
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
            upstream_url=config.upstream_url,
            upstream_model=config.upstream_model,
            upstream_api_key=config.upstream_api_key,
        )
    backend = BackendFactory.create(config)
    result = backend.generate(args.prompt, args.max_new_tokens)
    print(json.dumps(_result_to_dict(result), ensure_ascii=False, indent=2))
    return 0


def _mock_openai_chat(
    backend: InferenceBackend,
    config: BridgeConfig,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    messages = payload.get("messages") or []
    prompt = "\n".join(
        str(m.get("content", ""))
        for m in messages
        if isinstance(m, dict) and m.get("role") in ("user", "system")
    ).strip()
    max_new_tokens = int(payload.get("max_tokens") or config.max_new_tokens)
    result = backend.generate(prompt or "Say hello.", max_new_tokens)
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "model": payload.get("model") or config.model_id,
        "created": int(time.time()),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": result.response},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": max(1, len(prompt) // 4),
            "completion_tokens": max(1, len(result.response) // 4),
            "total_tokens": max(2, len(prompt) // 4 + len(result.response) // 4),
        },
        "zyrabit": {
            "mode": result.mode,
            "source": result.metrics.source,
            "backend": result.metrics.backend,
            "ttft_ms": None,
            "tps": None,
            "total_ms": result.elapsed_ms,
        },
    }


def _mock_openai_completions(
    backend: InferenceBackend,
    config: BridgeConfig,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    prompt = payload.get("prompt", "")
    if isinstance(prompt, list):
        prompt = " ".join(str(p) for p in prompt)
    max_new_tokens = int(payload.get("max_tokens") or config.max_new_tokens)
    result = backend.generate(str(prompt), max_new_tokens)
    return {
        "id": f"cmpl-{uuid.uuid4().hex[:12]}",
        "object": "text_completion",
        "model": payload.get("model") or config.model_id,
        "created": int(time.time()),
        "choices": [
            {
                "index": 0,
                "text": result.response,
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": max(1, len(str(prompt)) // 4),
            "completion_tokens": max(1, len(result.response) // 4),
            "total_tokens": max(2, len(str(prompt)) // 4 + len(result.response) // 4),
        },
        "zyrabit": {
            "mode": result.mode,
            "source": result.metrics.source,
            "backend": result.metrics.backend,
            "ttft_ms": None,
            "tps": None,
            "total_ms": result.elapsed_ms,
        },
    }


def run_server(config: BridgeConfig) -> None:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, ConfigDict, Field
    import uvicorn

    class GenerateRequest(BaseModel):
        prompt: str = Field(min_length=1, max_length=32_768)
        max_new_tokens: int = Field(default=config.max_new_tokens, ge=1, le=2_048)

    class OpenAIRequest(BaseModel):
        model_config = ConfigDict(extra="allow")

        model: Optional[str] = None
        messages: Optional[list[Dict[str, Any]]] = None
        prompt: Optional[Any] = None
        stream: bool = False
        max_tokens: Optional[int] = None

    app = FastAPI(
        title="Zyrabit-TT-Bridge",
        version="0.2.0",
        description="Tenstorrent OpenAI-compatible bridge for sovereign inference validation.",
    )
    backend = BackendFactory.create(config)
    metal_backend = backend if isinstance(backend, TenstorrentMetalBackend) else None

    @app.get("/v1/health")
    def health() -> Dict[str, Any]:
        return backend.health()

    @app.post("/v1/generate")
    def generate(request: GenerateRequest) -> Dict[str, Any]:
        try:
            return _result_to_dict(backend.generate(request.prompt, request.max_new_tokens))
        except Exception as exc:
            LOGGER.exception("Generation failed")
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/v1/models")
    async def models() -> Dict[str, Any]:
        if metal_backend is not None:
            return await metal_backend.models()
        return {
            "object": "list",
            "data": [
                {
                    "id": config.model_id,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "zyrabit",
                }
            ],
        }

    @app.post("/v1/chat/completions")
    async def chat_completions(request: OpenAIRequest) -> JSONResponse:
        payload = request.model_dump(exclude_unset=True)
        if metal_backend is not None:
            if payload.get("stream"):
                upstream = dict(payload)
                upstream["model"] = metal_backend.upstream_model
                upstream["stream"] = True
                started = time.perf_counter()

                async def _forward() -> AsyncIterator[str]:
                    async with httpx.AsyncClient(timeout=300.0) as client:
                        async with client.stream(
                            "POST",
                            f"{config.upstream_url}/v1/chat/completions",
                            json=upstream,
                            headers=metal_backend._headers(),
                        ) as resp:
                            if resp.status_code != 200:
                                raw = await resp.aread()
                                yield raw.decode(errors="replace")
                                return
                            async for line in resp.aiter_lines():
                                yield line + "\n"

                from fastapi.responses import StreamingResponse

                return StreamingResponse(_forward(), media_type="text/event-stream")
            result = await metal_backend._proxy_chat(payload)
        else:
            result = _mock_openai_chat(backend, config, payload)
        return JSONResponse(content=result)

    @app.post("/v1/completions")
    async def completions(request: OpenAIRequest) -> JSONResponse:
        payload = request.model_dump(exclude_unset=True)
        if metal_backend is not None:
            result = await metal_backend._proxy_completions(payload)
        else:
            result = _mock_openai_completions(backend, config, payload)
        return JSONResponse(content=result)

    uvicorn.run(app, host=config.host, port=config.port, log_level="info")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Zyrabit Tenstorrent bridge")
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
    if getattr(args, "host", None) or getattr(args, "port", None):
        config = BridgeConfig(
            model_id=config.model_id,
            mode=config.mode,
            host=args.host or config.host,
            port=args.port or config.port,
            max_new_tokens=config.max_new_tokens,
            wormhole_clock_hz=config.wormhole_clock_hz,
            min_ram_gb=config.min_ram_gb,
            allow_remote_model=config.allow_remote_model,
            upstream_url=config.upstream_url,
            upstream_model=config.upstream_model,
            upstream_api_key=config.upstream_api_key,
        )
    run_server(config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
