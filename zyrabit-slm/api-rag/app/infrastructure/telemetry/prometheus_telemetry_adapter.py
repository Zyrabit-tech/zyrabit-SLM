import logging
from typing import Any, Dict, Optional, ContextManager
from contextlib import contextmanager, nullcontext
import time

from app.domain.ports.telemetry_port import TelemetryPort

logger = logging.getLogger("zyrabit.telemetry")

# Prometheus metrics importados de forma lazy para entornos sin servidor
try:
    from prometheus_client import Histogram, Counter, Gauge
    TTFT_HISTOGRAM = Histogram(
        "gen_ai_client_time_to_first_token_seconds",
        "Time to First Token (TTFT) in seconds",
        ["model", "device"],
        buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )
    TOKEN_USAGE_COUNTER = Counter(
        "gen_ai_client_token_usage_total",
        "Total token usage by type (prompt vs completion)",
        ["model", "token_type"],
    )
    THROUGHPUT_GAUGE = Gauge(
        "gen_ai_server_tokens_per_second",
        "Generation throughput in tokens per second",
        ["model", "device"],
    )
    RAG_RETRIEVAL_HISTOGRAM = Histogram(
        "zyrabit_rag_retrieval_duration_seconds",
        "RAG hybrid retrieval duration in seconds",
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
    )
    SECURITY_AUDIT_COUNTER = Counter(
        "zyrabit_security_audit_total",
        "Total number of security audit events logged",
    )
    _prometheus_available = True
except ImportError:
    _prometheus_available = False


class PrometheusTelemetryAdapter(TelemetryPort):
    """
    Adaptador de Infraestructura: implementa TelemetryPort.
    Gestiona spans de observabilidad (OpenTelemetry) y métricas de Prometheus.
    """

    def log_security_audit(self, prompt: str) -> None:
        """Registra el prompt sanitizado con prefijo [SECURITY-AUDIT]."""
        logger.info(
            "[SECURITY-AUDIT] Prompt sanitizado recibido.",
            extra={"sanitized_prompt_length": len(prompt)},
        )
        if _prometheus_available:
            SECURITY_AUDIT_COUNTER.inc()

    def record_ttft(self, duration_ms: float, model: str = "default", device: str = "cpu") -> None:
        """Registra el tiempo al primer token (TTFT) en Prometheus."""
        duration_s = duration_ms / 1000.0
        logger.debug(f"[TTFT] {duration_ms:.2f} ms (model={model}, device={device})")
        if _prometheus_available:
            try:
                TTFT_HISTOGRAM.labels(model=model, device=device).observe(duration_s)
            except Exception:
                pass

    def record_tokens(self, prompt_tokens: int, completion_tokens: int, model: str = "default") -> None:
        """Registra tokens de entrada (prefill) y salida (decode)."""
        if _prometheus_available:
            try:
                if prompt_tokens > 0:
                    TOKEN_USAGE_COUNTER.labels(model=model, token_type="prompt").inc(prompt_tokens)
                if completion_tokens > 0:
                    TOKEN_USAGE_COUNTER.labels(model=model, token_type="completion").inc(completion_tokens)
            except Exception:
                pass

    def record_throughput(self, tps: float, model: str = "default", device: str = "cpu") -> None:
        """Registra tokens por segundo ($t/s$)."""
        if _prometheus_available:
            try:
                THROUGHPUT_GAUGE.labels(model=model, device=device).set(tps)
            except Exception:
                pass

    def record_rag_search(self, duration_ms: float, hits: int = 0) -> None:
        """Registra latencia de RAG e impactos de evidencia."""
        duration_s = duration_ms / 1000.0
        if _prometheus_available:
            try:
                RAG_RETRIEVAL_HISTOGRAM.observe(duration_s)
            except Exception:
                pass

    @contextmanager
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> ContextManager[Any]:
        """Inicia un span contextual de tiempo y traza."""
        t0 = time.time()
        logger.debug(f"[SPAN START] {name} | attrs={attributes or {}}")
        try:
            yield {"span_name": name, "start_time": t0, "attributes": attributes or {}}
        finally:
            elapsed_ms = (time.time() - t0) * 1000
            logger.debug(f"[SPAN END] {name} in {elapsed_ms:.2f} ms")
