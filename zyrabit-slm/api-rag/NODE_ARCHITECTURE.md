# Zyrabit Node: Technical Architecture

## Purpose

A local node ingests documents, preserves originals, generates evidence units, and responds strictly based on indexed evidence. The core engine does not spawn external connectors or unvetted agents.

## Flow

```
POST /v1/sources/import
  → local storage by SHA-256
  → SQLite job (queued → extracting → persisting_evidence → indexing_vectors → ready)
  → local parser → evidence units + FTS5 + optional vector index
POST /v1/query
  → FTS5 + optional vector search → evidence → local provider → response + sources
```

SQLite stores source metadata, document versions, jobs, evidence chunks, FTS indices, sessions, capabilities, and audit events. Files are stored by SHA-256 hash under `NODE_DATA_DIR/sources` to prevent filename collisions or overwrites.

## Ports & Adapters

The domain in `app/node` defines ports for source, parser, OCR, metadata, vector index, embeddings, reranking, and inference. Current adapters include local file storage, SQLite/FTS5, native local parsers, Chroma, and existing inference engine adapters. Ollama and llama.cpp are configured via environment variables; `SLM_URL` and `EMBEDDING_URL` are managed as separate network endpoints.

## Supported Formats

PDF retains exact page numbers; DOCX tracks paragraphs and tables; CSV/XLSX tracks worksheets and ranges; PPTX tracks slides and notes. Tesseract OCR is enabled only when `NODE_ENABLE_OCR=true` and only when a PDF page lacks selectable native text.

## Extensions

MCP, Telegram, Obsidian, AutoLearner, and auto-ingest components are preserved and loaded only when `ENABLE_LEGACY_EXTENSIONS=true`. Whisper transcription remains accessible via its dedicated endpoint.

## Local Operation

1. Configure `INFERENCE_PROVIDER`, `SLM_URL`, `EMBEDDING_URL`, `MODEL_NAME`, and `EMBEDDING_MODEL` in `zyrabit-slm/.env`.
2. Run `./zyra.sh install` or `./zyra.sh start`.
3. Query `GET /v1/health/capabilities`.
4. Import documents via `POST /v1/sources/import` and await `ready` state from `GET /v1/jobs/{job_id}`.

The legacy `POST /v1/ingest` endpoint is maintained for backwards compatibility, returning a durable job status rather than reporting immediate ingestion before completion.
