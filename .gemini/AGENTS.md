# Sovereign Agent Governance Rules

This document establishes the binding rules for AI Agent (Antigravity/Zyra) operations within the Zyrabit SLM project.

## 1. Deletion & Modification Policy
- **NO SILENT DELETION**: The Agent shall never delete a file or directory without explicit user consent.
- **RATIONALE REQUIRED**: Before requesting deletion, the Agent must present:
    1. The exact path.
    2. A description of the content.
    3. A technical rationale for the removal.
- **CONSENT CAPTURE**: Deletion is only permitted after the user responds with an affirmative (e.g., "Dale", "Yes", "Confirm").

## 2. Architectural Integrity
- **HEXAGONAL ONLY**: All new logic must be placed in the established Hexagonal layers:
    - `api/`: Presentation/Driving adapters.
    - `domain/`: Business logic and Use Cases.
    - `infrastructure/`: Externally driven adapters (DB, LLM).
    - `core/`: Cross-cutting concerns (Security, Settings).
- **PORT ISOLATION**: Direct dependencies on external libraries must go through a Port interface.

## 3. Communication & Tone
- **TRANSPARENCY**: The Agent must inform the user of the branch they are working on.
- **SECURITY FIRST**: All code changes must respect the PII Guard and Gatekeeper principles.

## 4. Documentation
- **STALENESS PREVENTION**: Every major architectural change must be accompanied by an update to `CHANGELOG.md` and relevant `README.md` files.
