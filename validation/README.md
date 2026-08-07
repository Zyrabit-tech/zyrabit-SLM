# Validation pack

This folder contains reproducible stress and security validation artifacts for:

- `POST /v1/sources/import`
- `GET /v1/jobs/{id}`
- `POST /v1/query`
- `GET /v1/health/capabilities`

## Requirements

- k6 installed for load tests.
- Running stack (`./zyra.sh start` or `./zyra.sh install`).
- Local endpoint available on `http://localhost:8080`.
- A configured local inference and embedding provider for real-node acceptance.

## Real document acceptance

The primary acceptance flow uses the authorized
`api-rag/docs/zyrabit-cioreview-en.pdf`. It imports the real PDF, waits for
`ready`, queries it, and rejects any response without a source from that exact
document and a page locator:

```bash
./validation/scripts/smoke_node_real.sh
```

This is intentionally separate from unit tests: it uses the configured local
model and index, not a test double. It is safe to repeat because identical
content is deduplicated.

For normal operation use `NODE_RETRIEVAL_MODE=hybrid`, which requires both a
reachable embedding provider and the vector index. If the machine deliberately
runs without embeddings, set `NODE_RETRIEVAL_MODE=lexical`; the response receipt
will say `evidence-query-lexical` rather than pretending semantic retrieval ran.

## Stress tests

```bash
k6 run validation/k6/chat_steady.js
k6 run validation/k6/chat_spike.js
k6 run validation/k6/chat_soak.js
k6 run validation/k6/ingest_concurrent.js
```

## Pentest checklist

See `validation/pentest/checklist.md`.
