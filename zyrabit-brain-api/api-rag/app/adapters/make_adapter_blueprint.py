"""Blueprint adapter for Make.com style webhook integrations."""

import hashlib
import hmac
from dataclasses import dataclass
from typing import Callable, Dict

from ..ports.automation_port import AutomationPort


@dataclass(frozen=True)
class MakeIntegrationPolicy:
    """Reference policy contract for a Make adapter implementation."""

    service_token: str
    signing_secret: str
    signature_header: str = "x-make-signature"


class MakeAdapterBlueprint(AutomationPort):
    """
    Generic blueprint for future Make adapter implementations.

    Replace this with provider-specific parsing rules as needed.
    """

    def __init__(
        self,
        policy: MakeIntegrationPolicy,
        execute_automation: Callable[[str], str],
    ) -> None:
        self.policy = policy
        self.execute_automation = execute_automation

    def authorize_request(
        self,
        authorization_header: str,
        signature_header: str,
        raw_body: bytes,
    ) -> None:
        token = self._extract_bearer_token(authorization_header)
        if not hmac.compare_digest(token, self.policy.service_token):
            raise PermissionError("Invalid Make bearer token.")

        expected_signature = self._build_signature(raw_body)
        if not hmac.compare_digest(signature_header.strip(), expected_signature):
            raise PermissionError("Invalid Make webhook signature.")

    def handle_payload(self, payload: Dict[str, object]) -> Dict[str, object]:
        text = str(payload.get("text", "")).strip()
        if not text:
            raise ValueError("Payload must include a non-empty 'text' field.")

        return {
            "status": "processed",
            "provider": "make",
            "scenario_id": str(payload.get("scenario_id", "unknown")),
            "execution_id": str(payload.get("execution_id", "unknown")),
            "response": self.execute_automation(text),
        }

    @staticmethod
    def _extract_bearer_token(authorization_header: str) -> str:
        if not authorization_header:
            return ""
        parts = authorization_header.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return ""
        return parts[1].strip()

    def _build_signature(self, raw_body: bytes) -> str:
        digest = hmac.new(
            key=self.policy.signing_secret.encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha256,
        ).hexdigest()
        return f"sha256={digest}"
