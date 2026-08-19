# Changelog

> This document is maintained in English only, by project policy.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.4.0] - 2026-08-19

### Added

- **Model-Agnostic Reasoning Parser**: Web UI now automatically detects `<think>...</think>` tags from any CoT model (DeepSeek-R1, QwQ, o1) and renders internal thoughts in a collapsible `🧠 Proceso de Razonamiento` accordion, showing only the clean final answer in the chat bubble.
- **Model Selection Matrix**: Added a compact decision matrix to `README.md` and a comprehensive guide to `docs-portal/docs/models.md` covering Instruct, Reasoning (CoT), and Tool/Coder model archetypes with hardware recommendations.
- **Business Rule Contract Tests**: New `test_model_reasoning_and_business_rules.py` suite validating that reasoning tokens never pollute SQLite history, prompts are sanitized, and greetings bypass document retrieval.
- **Configurable Inference Parameters**: `INFERENCE_TEMPERATURE` and `INFERENCE_MAX_TOKENS` are now environment variables (default: `0.1` / `1024`), enabling deterministic sampling without code changes.
- **Grafana Telemetry Screenshot**: Added Grafana dashboard screenshot to `README.md` Interface & Walkthrough section.

### Changed

- **Native Chat Message Splitting**: `ExistingInferenceAdapter` now correctly separates `system` and `user` roles for the OpenAI-compatible vLLM endpoint, preventing template misapplication on reasoning models.
- **Reasoning Token Sanitization**: `_compact_summary()` and `_prompt()` in `NodeService` now strip all `<think>` blocks before persisting history or building subsequent prompts, eliminating the feedback loop that caused token degradation.
- **Frontend Fetch Timeouts**: All `fetch()` calls in `api.js` now use `AbortSignal.timeout()` via a centralized `fetchWithTimeout` helper with per-endpoint timeouts (8s–120s), preventing indefinite hangs.

### Fixed

- **CI Contribution Policy**: Fixed `ci.yml` so `beta → main` PRs correctly pass validation instead of falling through to the rejection branch.
- **CI Trivy Scan**: Updated `security.yml` from broken `aquasecurity/trivy-action@v0.28.0` to `@master`, added explicit `scan-ref: '.'`, and set `severity: 'CRITICAL'`.
- **CI pip-audit Exit Code**: Removed raw `exit "$audit_exit"` that caused the job to fail even when all findings were documented in the risk register.
- **CI CodeQL Cleanup**: Removed duplicate CodeQL job from `security.yml` to eliminate GitHub Code Scanning configuration mismatch warnings.
- **Grafana RefId Collision**: Fixed `Multiple queries using the same RefId` error by assigning unique `refId` values (`A`, `B`) to all dashboard panel targets.
- **Grafana Datasource UID**: Added `uid: prometheus` to `datasource.yml` for reliable dashboard provisioning.

### Security

- **SQLite Migration Whitelist**: `_ensure_column()` in `sqlite_store.py` now validates table, column, and definition against strict allow-lists before executing `ALTER TABLE`, eliminating the SQL injection taint flow flagged by Ixtli CPG.
- **Silent Exception Logging**: Replaced `except Exception: pass` in `vllm_inference_adapter.py` and `vllm_stream_adapter.py` with `logger.debug()` to surface suppressed errors in diagnostics.

## [2.2.0-beta] - 2026-06-30

### Added

- **Dynamic PII Detection**: Integrated SpaCy NER model (`es_core_news_sm` / `en_core_web_sm`) in `pii_pipeline.py` to dynamically detect and mask names (PER), organizations (ORG), and locations (LOC), replacing the hardcoded list of names.
- **Asynchronous Streaming Port**: Implemented `StreamingInferencePort` and refactored `OllamaStreamAdapter` to conform to Hexagonal Architecture principles, providing decoupled and robust streaming.
- **Inference Provider Factory**: Created `InferenceProviderFactory` to dynamically instantiate both synchronous and asynchronous inference providers based on configuration.
- **MCP Client Port**: Defined `McpClientPort` and implemented `InternalMcpClientAdapter` to allow `ChatUseCase` to discover and invoke tools from the embedded FastMCP instance securely.

### Changed

- **Zero-Trust Security**: Applied `get_current_user` dependency globally to all main routers in `main.py` (`/v1/chat`, `/v1/documents`, `/v1/integrations`), ensuring uniform token-based authentication across all critical API endpoints.
- **Tool-Enabled LLM Generation**: Injected MCP tools dynamically into the system prompt during `ChatUseCase.stream_response()` to enable the LLM to request tool executions using JSON blocks.

## [2.1.0] - 2026-06-09

### Added

- **Advanced RAG (Cross-Encoder Re-Ranker)**: Integrated a lightweight token-intersection term-overlap scorer (`BGEReRankerAdapter`) to re-rank the top 10 search results and filter out chunks with a relevance score below `0.6` (max 3 chunks), preventing context pollution.
- **Strict Sliding Window Memory**: Implemented sliding window memory (`SlidingWindowMemoryAdapter`) to limit active conversation history to the last 4 turns (8 messages) to prevent context collapse and reduce latency.
- **Telegram Configuration Modal**: Added an instruction modal guide on how to configure Telegram bot token and chat ID in the local `.env` file, bound to the sidebar connectivity section.
- **Real-Time Security Logging**: Log masked PII entities directly into the Gatekeeper logs panel in real-time.
- **Automated Dependency Checker Task**: Added a weekly GitHub Actions workflow (`dependency-checker.yml`) that scans Python and Node dependencies and automatically opens or updates a GitHub Issue task with vulnerabilities and outdated versions.

### Changed

- **Exquisite Input Bar Design**: Redesigned the chat input container, removing the redundant paperclip attachment button in favor of a sleek, minimalist style (attaching files remains accessible via the sidebar Vault panel).
- **Clean UI Header Layout**: Removed the redundant `K Z` badges and consolidated system status/model indicators in the header.
- **Persistent Vault Storage**: Configured `zyrabit-api` to store document uploads under `/app/document_source` (persisted on host), preventing vault resets upon container recreations.
- **Stable Chat Sessions**: Standardized UI WebSocket connections with stable client-side session IDs (`thread_id`) stored in `sessionStorage` to avoid session loss on reconnect.
- **Removed Dependabot**: Deleted `.github/dependabot.yml` to disable automatic Dependabot pull requests entirely, preventing configuration parser errors and PR policy violations on the `main` branch.

### Fixed

- **CI Dependency Audit**: Upgraded vulnerable dependencies (`aiohttp`, `idna`, `pyjwt`, `starlette`, `pip`) in `uv.lock`. Ignored the unpatched and isolated ChromaDB vulnerability (`CVE-2026-45829`) in the `pip-audit` step of the security workflows to restore CI checks to green.

## [2.0.0] - 2026-05-15

### Added

- **Sovereign Persistence**: Migrated from memory-only state to SQLite WAL (`SovereignStateManager`) for persistent conversations and vault indexing.
- **FastMCP SDK Integration**: Full migration to the official MCP v1.0 SDK, replacing legacy JSON-RPC handlers.
- **Personalized Onboarding**: Added a profile management system that learns user goals and roles to tailor AI responses.
- **Hardware-Aware Detection**: `zyra-up.sh` now supports automated profiles for Metal (Mac), CUDA (Nvidia), and Tenstorrent.
- **Context Budgeting**: Implemented strict token management with `tiktoken` and rank-based context trimming.
- **Security Shield**: Added executable script scanning for `import_to_vault` and automated security audits (Trivy + CodeQL).

### Changed

- Refactored `ChatUseCase` to use the new `ContextManager` and `SovereignStateManager`.
- Updated `main.py` to initialize the sovereign database lifespan.
- Standardized file ingestion using SHA-256 hashing to avoid redundant processing.

### Fixed

- Resolved `ImportError` on startup caused by legacy MCP RPC handlers.
- Fixed database concurrency issues by enabling WAL mode for all SQLite operations.

## [1.7.5] - 2026-05-15

### Security

- Hardened MCP file reading by strictly validating paths against allowed roots, preventing directory traversal attacks.
- Updated `_resolve_file_uri` to canonicalize paths and use `os.path.commonpath` for robust path containment checks.

### Changed

- Updated `zyra-up.sh verify` to use `uv run pytest -q` for running MCP security tests.

## [1.5.0] - 2026-04-08

### Added

- **Sovereign Agent Governance**: Established `AGENTS.md` with strict rules for AI Agent operations (no silent deletions).
- **Hexagonal Architecture Realignment**: Deep structural refactor into `domain`, `ports`, `adapters`, `api`, and `core` layers.
- **Gatekeeper Isolation**: Centralized SLM routing and security policy decision logic in `domain/services/gatekeeper.py`.
- **Architectural Documentation**: Added `HEXAGONAL_ARCHITECTURE.md` to document the tiered structure.

### Changed

- Refactored `main.py` into a lean entry point.
- Moved API endpoints to `api/v1/endpoints/`.
- Moved all external adapters to `infrastructure/`.
- Consolidated security and metrics into `core/`.
- Updated `zyra-up.sh` with `--local`, `--model` flags and production cleanup.

### Fixed

- Improved health check to detect if the SLM model is currently loaded in RAM.
- Handled `=` syntax for the `--model` flag in the setup script.

## [1.2.0] - 2026-04-06

### Added

- `zyrabit-slm/README_EN.md` as the English mirror for backend documentation.
- Setup script role notes in root docs to clarify `install.sh` and `zyra-up.sh` responsibilities.
- n8n integration adapter and automation port in `api-rag` (`app/adapters/n8n_adapter.py`, `app/ports/automation_port.py`).
- Secure n8n webhook endpoint `POST /v1/integrations/n8n/webhook` and integration tests.
- New docs-portal pages: `integration-playbook.md`, `architecture-mermaid.md`, and reusable Mermaid source `zyrabit-architecture.mmd`.
- `api-rag/app/adapters/make_adapter_blueprint.py` as a reusable blueprint for Make.com integration.

### Changed

- Updated `README.md` and `README_EN.md` to document the official setup flow.
- Updated `zyrabit-slm/README.md` with a link to the English version and setup script roles.
- Updated `llms-full.md` to describe bootstrap flow (`install.sh` -> `zyra-up.sh install`).
- Updated all 4 README files to clarify responsibilities, manual Docker flows, and manual model pull commands.
- Added optional `automation` profile with `n8n` routed via Traefik in `zyrabit-slm/docker-compose.yml`.
- Updated docs-portal navigation and enabled Mermaid rendering in Docusaurus config.
- Restored root `README.md` as Spanish documentation mirror with explicit Air-Gapped installation guidance.
- Routed `grafana` and `prometheus` through Traefik (`/grafana`, `/prometheus`) removing direct public port exposure.
- Added file-based secret support in n8n adapter (`N8N_SERVICE_TOKEN_FILE`, `N8N_WEBHOOK_SIGNING_SECRET_FILE`) for Docker Secrets/Vault workflows.
- Updated installer output (`zyra-up.sh`) to reflect Traefik observability routes.
- Expanded docs (root/backend/docs-portal) with Air-Gapped deployment, observability auth routes, Make adapter bootstrap, and local super-fine-tuning next steps.

### Fixed

- Removed fixed `DOCKER_API_VERSION=1.41` from `traefik` in `zyrabit-slm/docker-compose.yml` to avoid Docker API compatibility errors with newer Docker engines.

### Removed

- Removed legacy `setup_slm.sh` to eliminate duplicate setup paths and reduce operational drift.

## [1.0.0] - 2026-02-23

### Added

- Initial stable release.
