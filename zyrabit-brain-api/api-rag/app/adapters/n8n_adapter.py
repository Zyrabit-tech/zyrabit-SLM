"""n8n adapter implementing the automation integration port."""

import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Callable, Dict

from ..ports.automation_port import AutomationPort


def _parse_bool(value: str, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class N8nIntegrationPolicy:
    """High-level policies for n8n integration security."""

    service_token: str
    signing_secret: str
    require_signature: bool = True

    @classmethod
    def from_env(cls) -> "N8nIntegrationPolicy":
        return cls(
            service_token=os.getenv("N8N_SERVICE_TOKEN", ""),
            signing_secret=os.getenv("N8N_WEBHOOK_SIGNING_SECRET", ""),
            require_signature=_parse_bool(os.getenv("N8N_REQUIRE_SIGNATURE"), True),
        )


class N8nAdapter(AutomationPort):
    """Adapter that validates n8n webhooks and invokes application use-cases."""

    def __init__(
        self,
        policy: N8nIntegrationPolicy,
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
        expected_token = self.policy.service_token
        if not expected_token:
            raise PermissionError("N8N_SERVICE_TOKEN is not configured.")

        received_token = self._extract_bearer_token(authorization_header)
        if not hmac.compare_digest(received_token, expected_token):
            raise PermissionError("Invalid n8n bearer token.")

        if self.policy.require_signature:
            if not self.policy.signing_secret:
                raise PermissionError("N8N_WEBHOOK_SIGNING_SECRET is not configured.")
            if not self._validate_signature(signature_header, raw_body):
                raise PermissionError("Invalid n8n webhook signature.")

    def handle_payload(self, payload: Dict[str, object]) -> Dict[str, object]:
        text = str(payload.get("text", "")).strip()
        if not text:
            raise ValueError("Payload must include a non-empty 'text' field.")

        workflow_id = str(payload.get("workflow_id", "unknown"))
        execution_id = str(payload.get("execution_id", "unknown"))
        response = self.execute_automation(text)

        return {
            "status": "processed",
            "provider": "n8n",
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "response": response,
        }

    @staticmethod
    def _extract_bearer_token(authorization_header: str) -> str:
        if not authorization_header:
            return ""
        parts = authorization_header.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return ""
        return parts[1].strip()

    def _validate_signature(self, signature_header: str, raw_body: bytes) -> bool:
        if not signature_header:
            return False
        expected_hash = hmac.new(
            key=self.policy.signing_secret.encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha256,
        ).hexdigest()
        expected_signature = f"sha256={expected_hash}"
        return hmac.compare_digest(signature_header.strip(), expected_signature)
