"""
Adoption & Usage Telemetry for Zyrabit Platform.
100% Privacy-Preserving, Zero-PII, Air-Gap Tolerant.

Users can disable telemetry at any time by setting:
  ZYRABIT_TELEMETRY_DISABLED=true
or
  DO_NOT_TRACK=1
"""

from __future__ import annotations

import os
import sys
import json
import uuid
import logging
import platform
import asyncio
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("zyrabit.telemetry.adoption")

DEFAULT_ENDPOINT = os.getenv("ZYRABIT_TELEMETRY_ENDPOINT", "https://telemetry.zyrabit.com/v1/heartbeat")


class AdoptionTelemetry:
    @staticmethod
    def is_disabled() -> bool:
        """Returns True if telemetry has been explicitly disabled."""
        if os.getenv("ZYRABIT_TELEMETRY_DISABLED", "").strip().lower() in ("true", "1", "yes"):
            return True
        if os.getenv("DO_NOT_TRACK", "").strip().lower() in ("true", "1", "yes"):
            return True
        if os.getenv("TESTING", "").strip().lower() == "true":
            return True
        return False

    @staticmethod
    def get_or_create_instance_id(storage_dir: str) -> str:
        """Retrieves or creates an anonymous installation UUID."""
        path = Path(storage_dir) / "telemetry_instance_id.txt"
        try:
            if path.exists():
                val = path.read_text().strip()
                if val:
                    return val
            new_id = str(uuid.uuid4())
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new_id)
            return new_id
        except Exception:
            return "ephemeral-" + str(uuid.uuid4())[:8]

    @classmethod
    def collect_payload(cls, storage_dir: str = "/tmp") -> Dict[str, Any]:
        """Assembles non-PII operational telemetry."""
        from app.infrastructure.shared.config import (
            PROJECT_NAME, MODEL_NAME, NODE_RETRIEVAL_MODE, NODE_ENABLE_OCR
        )

        instance_id = cls.get_or_create_instance_id(storage_dir)
        is_container = os.path.exists("/.dockerenv") or os.getenv("CONTAINER") == "true"
        
        return {
            "instance_id": instance_id,
            "project": PROJECT_NAME,
            "version": os.getenv("VERSION", "2.1.0"),
            "os_system": platform.system(),
            "os_machine": platform.machine(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "execution_environment": "docker" if is_container else "host_native",
            "active_provider": os.getenv("INFERENCE_PROVIDER", "ollama"),
            "active_model": MODEL_NAME,
            "retrieval_mode": NODE_RETRIEVAL_MODE,
            "ocr_enabled": NODE_ENABLE_OCR,
        }

    @classmethod
    async def send_heartbeat(cls, storage_dir: str = "/tmp") -> bool:
        """Sends a non-blocking anonymous heartbeat ping. Returns False if disabled or failed."""
        if cls.is_disabled():
            logger.info("🔒 Adoption telemetry is disabled (air-gapped / opt-out mode).")
            return False

        payload = cls.collect_payload(storage_dir)

        # Write local audit log so the administrator can inspect telemetry transparency
        try:
            audit_path = Path(storage_dir) / "telemetry_audit.json"
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            audit_path.write_text(json.dumps(payload, indent=2))
        except Exception:
            pass

        # Send heartbeat with very strict timeout (2.0s max)
        try:
            import httpx
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.post(DEFAULT_ENDPOINT, json=payload)
                if res.status_code < 300:
                    logger.debug("✔ Adoption heartbeat sent successfully.")
                    return True
        except Exception as exc:
            # Tolerates offline/air-gapped environments without failing
            logger.debug(f"ℹ Telemetry endpoint unreachable (offline/air-gap mode): {exc}")

        return False
