"""
AG-UI Endpoint for Zyrabit SLM.

POST /ag-ui — Emits an SSE stream of AG-UI typed events.
Compatible with CopilotKit v2+ frontends.

This is the Primary Adapter in our Hexagonal Architecture:
    Request → Auth Check (get_current_user)
            → ChatUseCase.mask_query (PII Sanitization)
            → ChatUseCase.stream_response (Streaming Inference & RAG)
            → ChatUseCase.save_interaction (Sovereign DB Storage)
            → StateAggregatorUseCase (Vault Snapshot)
            → AG-UI EventEncoder (SSE Output)

Security:
    - Zero-Trust: Mandatory Bearer Token authentication.
    - Leak Prevention: Monitored client disconnection.
    - Boundary Isolation: No database or model-network direct details.
"""

from __future__ import annotations

import uuid
import logging
import asyncio
from typing import AsyncIterator

from fastapi import APIRouter, Depends, Security, Request
from fastapi.responses import StreamingResponse

# pyrefly: ignore [missing-import]
from ag_ui.core import (
    RunAgentInput,
    EventType,
    RunStartedEvent,
    RunFinishedEvent,
    RunErrorEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    StateSnapshotEvent,
)
# pyrefly: ignore [missing-import]
from ag_ui.encoder import EventEncoder

from app.core.security import get_current_user
from app.domain.use_cases.chat_use_case import ChatUseCase
from app.application.use_cases.state_aggregator_use_case import StateAggregatorUseCase
from app.api.v1.dependencies import get_chat_use_case, get_state_aggregator

logger = logging.getLogger("zyrabit.agui")

router = APIRouter(tags=["AG-UI"])


@router.post(
    "/",
    summary="AG-UI compatible streaming endpoint",
    description=(
        "Accepts RunAgentInput and emits an SSE stream of AG-UI events. "
        "All inference is local (Ollama). PII scrubbing applied before inference. "
        "Requires Bearer authentication. Resilient to connection drops."
    ),
)
async def ag_ui_endpoint(
    request: Request,
    input_data: RunAgentInput,
    current_user=Security(get_current_user),
    chat_use_case: ChatUseCase = Depends(get_chat_use_case),
    state_aggregator: StateAggregatorUseCase = Depends(get_state_aggregator),
):
    """
    AG-UI streaming endpoint.
    Emits events compatible with CopilotKit v2+ frontends.
    Enforces authentication and prevents connection/task leaks.
    """
    return StreamingResponse(
        _ag_ui_stream(request, input_data, chat_use_case, state_aggregator),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Zyrabit-Version": "2.0.0",
            "X-Zyrabit-Mode": "sovereign",
        },
    )


async def _ag_ui_stream(
    request: Request,
    input_data: RunAgentInput,
    chat_use_case: ChatUseCase,
    state_aggregator: StateAggregatorUseCase,
) -> AsyncIterator[str]:
    """
    Core AG-UI event generator.
    Hexagonal Architecture: Completely isolated from DB/infrastructure details.
    Checks client disconnection to prevent leaks.
    """
    encoder = EventEncoder()
    thread_id = input_data.thread_id or str(uuid.uuid4())
    run_id = input_data.run_id or str(uuid.uuid4())
    msg_id = str(uuid.uuid4())

    try:
        # ── 1. RUN_STARTED ────────────────────────────────────────
        yield encoder.encode(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=thread_id,
            run_id=run_id,
        ))

        # ── 2. Extract user message ───────────────────────────────
        user_message = ""
        for m in reversed(input_data.messages):
            if m.role == "user":
                user_message = m.content
                break

        if not user_message:
            yield encoder.encode(RunErrorEvent(
                type=EventType.RUN_ERROR,
                message="No user message found in input",
                code="EMPTY_INPUT",
            ))
            return

        # ── 3. PII Scrubbing (Delegated to Domain Use Case) ───────
        clean_message, pii_detected = chat_use_case.mask_query(user_message)
        if pii_detected:
            logger.info("🛡️ AG-UI: PII scrubbed inside domain layer")

        # ── 4. Retrieve User Profile
        from app.infrastructure.shared.state_tracker import SovereignStateManager
        user_profile = SovereignStateManager.get_user_profile()

        # Convert AG-UI messages to history format
        history = []
        for m in input_data.messages[:-1]:  # Exclude last (current) message
            history.append({"role": m.role, "content": m.content})

        # ── 5. TEXT_MESSAGE_START ─────────────────────────────────
        yield encoder.encode(TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START,
            message_id=msg_id,
            role="assistant",
        ))

        # ── 6. Stream tokens via ChatUseCase (Anti-Leak Check) ───
        full_response = []
        rag_hits = 0

        async for chunk in chat_use_case.stream_response(
            clean_query=clean_message,
            history=history,
            user_profile=user_profile,
        ):
            # Check client disconnection to prevent task/model-network leaks
            if await request.is_disconnected():
                logger.info("🔌 Client disconnected abruptly. Aborting stream.")
                return

            if isinstance(chunk, dict):
                # The generator yields a dict of metadata at the end
                rag_hits = chunk.get("rag_hits", 0)
                break

            full_response.append(chunk)
            yield encoder.encode(TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id=msg_id,
                delta=chunk,
            ))

        # Check disconnection after loop
        if await request.is_disconnected():
            return

        # ── 7. TEXT_MESSAGE_END ────────────────────────────────────
        yield encoder.encode(TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END,
            message_id=msg_id,
        ))

        # ── 8. Persist to Sovereign DB (Delegated to Use Case) ─────
        response_text = "".join(full_response)
        chat_use_case.save_interaction(thread_id, clean_message, response_text)

        # ── 9. STATE_SNAPSHOT ────────────────────────────────────
        snapshot = await state_aggregator.execute()
        snapshot["pii_detected"] = pii_detected
        snapshot["rag_hits"] = rag_hits

        yield encoder.encode(StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT,
            snapshot=snapshot,
        ))

        # ── 10. RUN_FINISHED ─────────────────────────────────────
        yield encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=thread_id,
            run_id=run_id,
        ))

    except asyncio.CancelledError:
        logger.info("🔌 Context cancelled by client connection drop.")
    except Exception as exc:
        logger.exception("❌ AG-UI stream error: %s", exc)
        yield encoder.encode(RunErrorEvent(
            type=EventType.RUN_ERROR,
            message=str(exc),
            code="ZYRABIT_INTERNAL_ERROR",
        ))
