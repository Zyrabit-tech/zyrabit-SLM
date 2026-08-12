# Evidence Boundary Hardening

## Purpose

Mitigate risks preventing a verifiable technical beta of the document node. System startup alone is not the success criterion: the node must import, persist, survive restarts, recover evidence from the selected document, and clearly communicate any degradation to the user.

## Committed Changes

1. **Secure Persistence** — The runtime will not use an ephemeral vector index as a fallback. If Chroma is unavailable, it will declare degraded capacity and block vector indexing.
2. **Recovery** — Re-indexing from hash-stored source documents will be added; original sources will be preserved and durable background jobs created.
3. **Observable Health** — Both API and Web will feature verifiable health checks exposing storage, FTS, vector index, inference, embeddings, OCR, and operational status.
4. **Evidence Receipt** — The UI will render document origin, location, excerpt, provider, decision, and latency; extractive fallback will be explicitly visible.
5. **Reproducible Gates** — A post-build smoke test will be introduced: clean images, compose launch, health checks, authorized PDF ingestion, evidence query, and teardown.
6. **Dependency Risk Management** — Unpatched vulnerabilities will be logged with date, mitigation strategy, and review owner rather than silently ignored in CI.

## Out of Scope

- Legacy runtime is preserved behind `ENABLE_LEGACY_EXTENSIONS` without deletion or rewrite.
- No cloud providers or model changes will be introduced without explicit approval.
- Synthetic documents will not be used for product acceptance or demonstration.

## Exit Criteria

1. `pytest`, web compilation, and lockfile validation pass.
2. Newly built API and Web images start with passing health checks.
3. After importing `zyrabit-cioreview-en.pdf`, a query returns evidence matching the exact document and page.
4. Following a stack restart, the document can be re-indexed and queried without silent data loss.
5. Outages in Chroma, embeddings, or inference present as visible degradation, never false positives.
