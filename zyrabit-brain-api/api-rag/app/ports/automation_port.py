"""Port definitions for external automation integrations."""

from abc import ABC, abstractmethod
from typing import Dict


class AutomationPort(ABC):
    """Abstraction for workflow automation providers (n8n, Make, etc.)."""

    @abstractmethod
    def authorize_request(
        self,
        authorization_header: str,
        signature_header: str,
        raw_body: bytes,
    ) -> None:
        """Validate integration credentials and request integrity."""

    @abstractmethod
    def handle_payload(self, payload: Dict[str, object]) -> Dict[str, object]:
        """Transform provider payload into a domain-level automation request."""
