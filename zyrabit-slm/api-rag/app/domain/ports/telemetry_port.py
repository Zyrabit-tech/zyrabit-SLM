import abc

class TelemetryPort(abc.ABC):
    """
    Puerto de Telemetría (Dominio).
    Aísla la lógica de aplicación de la infraestructura de logs y monitoreo (ej. Prometheus).
    """

    @abc.abstractmethod
    def log_security_audit(self, prompt: str) -> None:
        """Registra el prompt sanitizado por razones de auditoría y seguridad PII."""
        pass

    @abc.abstractmethod
    def record_ttft(self, duration_ms: float) -> None:
        """Registra el Time To First Token (TTFT) en la infraestructura de métricas."""
        pass
