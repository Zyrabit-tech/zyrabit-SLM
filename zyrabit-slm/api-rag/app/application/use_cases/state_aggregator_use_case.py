"""
StateAggregatorUseCase — Composes sovereign infrastructure state for AG-UI.

This use case aggregates data from SovereignStateManager and ObsidianService
into a single DTO suitable for the AG-UI StateSnapshotEvent.

Architecture Note:
    Application Layer use case (Hexagonal Architecture).
    Injects infrastructure dependencies via constructor.
    Returns a plain dict — no AG-UI coupling in this layer.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.infrastructure.shared.state_tracker import SovereignStateManager
from app.infrastructure.shared.config import MODEL_NAME

logger = logging.getLogger("zyrabit.agui.state")


class StateAggregatorUseCase:
    """
    Composes a unified state snapshot from Sovereign State and Obsidian.

    The returned dict is consumed by the AG-UI endpoint to emit
    a StateSnapshotEvent, giving the CopilotKit frontend visibility
    into vault health, PII metrics, and inference configuration.
    """

    async def execute(self) -> Dict[str, Any]:
        """
        Aggregate stats from SovereignStateManager and user profile.

        Returns:
            Dict with keys: vault_docs, total_tokens, total_messages,
            inference_model, user_profile, and db_path.
        """
        try:
            stats = SovereignStateManager.get_stats()
            profile = SovereignStateManager.get_user_profile()

            return {
                "vault_docs": stats.get("vault_files", 0),
                "total_tokens": stats.get("total_tokens", 0),
                "total_messages": stats.get("total_messages", 0),
                "inference_model": profile.get("preferred_model", MODEL_NAME),
                "assistant_name": profile.get("assistant_name", "Zyra"),
                "persona": profile.get("persona", "general"),
                "db_path": stats.get("db_path", "unknown"),
            }
        except Exception as exc:
            logger.error("Failed to aggregate sovereign state: %s", exc)
            return {
                "vault_docs": -1,
                "total_tokens": -1,
                "total_messages": -1,
                "inference_model": MODEL_NAME,
                "error": str(exc),
            }
