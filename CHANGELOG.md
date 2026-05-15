# Changelog

> This document is maintained in English only, by project policy.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
