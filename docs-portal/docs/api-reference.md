# API Reference

Zyrabit SLM provides a robust REST API for document ingestion and inference. It is designed to be partially compatible with the OpenAI API specification to simplify integration with existing AI tools and libraries.

## Core Endpoints

### 1. Chat Completion (`POST /v1/chat`)

Generates a response based on a prompt and context retrieved from the vector database.

**Request Body:**
```json
{
  "model": "qwen2.5:7b",
  "messages": [
    {
      "role": "user",
      "content": "What is our internal travel policy?"
    }
  ],
  "stream": false,
  "temperature": 0.7
}
```

**Success Response (200 OK):**
```json
{
  "id": "chat-123",
  "object": "chat.completion",
  "created": 1677652288,
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Our internal travel policy requires..."
      },
      "finish_reason": "stop"
    }
  ]
}
```

### 2. Document Ingestion (`POST /v1/ingest`)

Uploads and vectorizes documents for future RAG queries.

**Request Body (Multipart Form Data):**
- `file`: The document file (PDF, TXT, MD).
- `collection`: (Optional) The name of the vector collection. Defaults to `zyrabit-default`.

**Success Response (201 Created):**
```json
{
  "status": "success",
  "document_id": "doc-456",
  "chunks": 42
}
```

### 3. Model Management (`GET /v1/models`)

Lists all models currently available in the local inference engine.

**Success Response (200 OK):**
```json
{
  "object": "list",
  "data": [
    {
      "id": "qwen2.5:7b",
      "object": "model",
      "owned_by": "zyrabit"
    }
  ]
}
```

## Error Codes

| HTTP Status | Code | Description |
| :--- | :--- | :--- |
| 400 | `bad_request` | The request payload is malformed or missing required fields. |
| 401 | `unauthorized` | Missing or invalid authentication token. |
| 404 | `not_found` | The requested model or document does not exist. |
| 500 | `internal_error` | An unexpected error occurred on the server (e.g., inference engine crash). |

## Authentication

All requests must include a valid service token in the Authorization header:

```bash
Authorization: Bearer <YOUR_SERVICE_TOKEN>
```
