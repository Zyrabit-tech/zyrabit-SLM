"""
FASE 2 - Paso 4: Adaptador de Infraestructura para Telemetría.

Este módulo es la única capa donde se importan prometheus_client y logging.
El dominio (chat_use_case.py) nunca debe importar nada de aquí.
"""
import logging
from app.domain.ports.telemetry_port import TelemetryPort

logger = logging.getLogger("zyrabit.telemetry")

# Prometheus histogram importado de forma lazy para no romper tests unitarios
# que no levantan el servidor completo.
try:
    from prometheus_client import Histogram, Counter
    TTFT_HISTOGRAM = Histogram(
        "zyrabit_ttft_seconds",
        "Time to First Token (TTFT) in seconds",
        buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
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
    Registra eventos de seguridad en el log estructurado y métricas TTFT en Prometheus.
    """

    def log_security_audit(self, prompt: str) -> None:
        """Registra el prompt sanitizado con prefijo [SECURITY-AUDIT]."""
        logger.info(
            "[SECURITY-AUDIT] Prompt sanitizado recibido.",
            extra={"sanitized_prompt_length": len(prompt)},
        )
        if _prometheus_available:
            SECURITY_AUDIT_COUNTER.inc()

    def record_ttft(self, duration_ms: float) -> None:
        """Registra el tiempo al primer token (TTFT) en Prometheus."""
        duration_s = duration_ms / 1000.0
        logger.debug(f"[TTFT] {duration_ms:.2f} ms")
        if _prometheus_available:
            TTFT_HISTOGRAM.observe(duration_s)
