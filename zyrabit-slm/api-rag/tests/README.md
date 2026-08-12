# Node Test Strategy

The main test suite executes with `PYTHONPATH=zyrabit-slm/api-rag .venv/bin/python -m pytest`.

| Group | Purpose | Gate Criterion |
| --- | --- | --- |
| `tests/node` | Ingestion, jobs, FTS, document scope isolation, and cited responses | Release Blocking |
| Security & Inference | Authentication, PII protection, and provider contracts | Release Blocking |
| `tests/legacy` | MCP, ReAct, n8n, legacy chat/cache, and previous ingest script | Preserved, non-blocking |

Document acceptance tests utilize `api-rag/docs/zyrabit-cioreview-en.pdf` and the Prospeo Playbook stored in `document_source`. Model mocks and manufactured documents are not accepted as production evidence.

Prior to demonstration, execute the primary test suite and, with Docker containers running, run the physical validation workflow: import → `ready` → select → query → verify source page and excerpt citations.
