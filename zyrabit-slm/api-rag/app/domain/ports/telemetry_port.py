import abc
from typing import Any, Dict, Optional, ContextManager


class TelemetryPort(abc.ABC):
    """
    Puerto de Telemetría (Dominio).
    Aísla la lógica de aplicación de la infraestructura de logs, OpenTelemetry y Prometheus.
    """

    @abc.abstractmethod
    def log_security_audit(self, prompt: str) -> None:
        """Registra el prompt sanitizado por razones de auditoría y seguridad PII."""
        pass

    @abc.abstractmethod
    def record_ttft(self, duration_ms: float, model: str = "default", device: str = "cpu") -> None:
        """Registra el Time To First Token (TTFT) en la infraestructura de métricas."""
        pass

    @abc.abstractmethod
    def record_tokens(self, prompt_tokens: int, completion_tokens: int, model: str = "default") -> None:
        """Registra el conteo de tokens de prefill y decode."""
        pass

    @abc.abstractmethod
    def record_throughput(self, tps: float, model: str = "default", device: str = "cpu") -> None:
        """Registra la velocidad de generación en tokens por segundo."""
        pass

    @abc.abstractmethod
    def record_rag_search(self, duration_ms: float, hits: int = 0) -> None:
        """Registra la duración de la búsqueda híbrida y los hits encontrados."""
        pass

    @abc.abstractmethod
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> ContextManager[Any]:
        """Inicia un span de trazabilidad distribuida (OpenTelemetry)."""
        pass

