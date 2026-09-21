---
sidebar_position: 1
title: 'API Reference'
description: 'REST API endpoints for chat, document ingestion, structured extraction, and health diagnostics'
---

# API Reference

Zyrabit Platform exposes a hardened, evidence-bound REST API for local document ingestion, private inference, structured JSON extraction, and runtime diagnostics.

All endpoints are hosted under `/v1` and enforce local Bearer token authentication.

---

## Authentication

All protected requests must include a valid service token in the `Authorization` header:

```http
Authorization: Bearer <YOUR_API_TOKEN>
```

In the standard platform container distribution, this corresponds to the token set via `API_KEY` (or the dynamic runtime token provided to the web UI).

---

## Core Endpoints

### 1. Chat Completion (`POST /v1/chat`)

Primary inference and RAG endpoint. Sanitizes PII before inference, searches local BM25/vector indexes, and formats evidence-bound responses.

**Request Body (`application/json`):**

```json
{
  "text": "What is our internal travel policy?",
  "session_id": "optional-session-id",
  "document_id": "optional-document-id",
  "history": []
}
```

| Parameter | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `text` | `string` | **Yes** | User question or command. |
| `session_id` | `string` | No | ID for conversation session context and SQLite WAL persistence. |
| `document_id` | `string` | No | Scope query to a specific document index. |
| `history` | `array` | No | Previous turns in the conversation. |

**Success Response (`200 OK`):**

```json
{
  "response": "According to the travel policy, all flights over 4 hours must be approved...",
  "metadata": {
    "decision": "hybrid-rag",
    "sources": ["travel_policy.pdf"],
    "rag_hits": 2,
    "provider": "ollama",
    "latency_seconds": 0.84,
    "tps": 88.5
  }
}
```

---

### 2. Document Ingestion (`POST /v1/sources/import` or `POST /v1/ingest`)

Uploads and vectorizes documents (PDF, DOCX, TXT, MD, CSV, Audio) into the sovereign vault.

**Request Body (`multipart/form-data`):**
- `file`: The binary document file to import.

**Success Response (`200 OK`):**

```json
{
  "status": "accepted",
  "document_id": "doc_9f8e7d",
  "job_id": "job_1a2b3c",
  "filename": "travel_policy.pdf",
  "message": "File accepted. Poll the job until it is indexed and ready for retrieval."
}
```

---

### 3. List Documents (`GET /v1/documents`)

Lists all documents currently indexed in the sovereign vault.

**Success Response (`200 OK`):**

```json
{
  "documents": [
    {
      "id": "doc_9f8e7d",
      "filename": "travel_policy.pdf",
      "chunks": 18,
      "created_at": "2026-09-14T10:00:00Z"
    }
  ]
}
```

---

### 4. Structured Extraction (`POST /v1/extract`)

Extracts schema-conforming JSON entities from unstructured text with automatic schema validation.

**Request Body (`application/json`):**

```json
{
  "text": "Invoice #10293 for ACME Corp, amount $4,500.00 USD dated 2026-09-12.",
  "schema_definition": {
    "type": "object",
    "properties": {
      "invoice_number": { "type": "string" },
      "vendor": { "type": "string" },
      "amount": { "type": "number" },
      "currency": { "type": "string" }
    },
    "required": ["invoice_number", "vendor", "amount"]
  }
}
```

**Success Response (`200 OK`):**

```json
{
  "data": {
    "invoice_number": "10293",
    "vendor": "ACME Corp",
    "amount": 4500.0,
    "currency": "USD"
  },
  "valid": true,
  "errors": [],
  "raw_response": "{\"invoice_number\": \"10293\", ...}",
  "model": "qwen2.5:1.5b"
}
```

---

### 5. Health & Diagnostic Receipt (`GET /v1/health`)

Returns an operational verification receipt of the platform, vector database, and local inference engine.

**Success Response (`200 OK`):**

```json
{
  "status": "OPERATIONAL",
  "timestamp": "2026-09-20T18:00:00.000000",
  "metadata": {
    "project": "Zyrabit SLM",
    "version": "2.4.4",
    "uptime": "1:23:45",
    "system": {
      "cpu_usage": "12.5%",
      "ram_usage": "45.2%",
      "platform": "Darwin",
      "arch": "arm64"
    }
  },
  "infrastructure": [
    { "id": "core-api", "name": "Zyrabit Core API", "status": "ONLINE", "type": "Runtime" },
    { "id": "vector-db", "name": "ChromaDB Vector Index", "status": "ONLINE", "type": "Persistence", "metrics": { "documents": 5 } },
    { "id": "slm-engine", "name": "Ollama (qwen2.5:1.5b)", "status": "ONLINE", "type": "Inference" }
  ],
  "capabilities": []
}
```

---

## Error Codes

| HTTP Status | Detail | Description |
| :--- | :--- | :--- |
| `400 Bad Request` | `Invalid payload` | Missing required fields or unparseable input. |
| `401 Unauthorized` | `Not authenticated: Bearer token required` | Missing or invalid API key in `Authorization` header. |
| `404 Not Found` | `Resource not found` | The requested document, job, or session does not exist. |
| `422 Unprocessable` | `Validation Error` | Pydantic schema validation failure on request payload. |
| `503 Service Unavailable` | `Inference provider is offline` | The local SLM engine (Ollama/vLLM/llama.cpp) is unreachable. |

---

## Related Documentation

- [Integration Playbook](./integration-playbook.md)
- [Hexagonal Architecture](./architecture/hexagonal.md)
- [Production Hardening](./production-hardening.md)
