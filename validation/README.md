# Architecture Validation Pack

This folder contains reproducible stress and security validation artifacts for:

- `POST /v1/chat`
- `POST /v1/ingest`
- `POST /mcp`
- `POST /v1/integrations/n8n/webhook`

## Requirements

- k6 installed for load tests.
- Running stack (`./zyra-up.sh start` or `./zyra-up.sh install`).
- Local endpoint available on `https://localhost`.

## Stress tests

```bash
k6 run validation/k6/chat_steady.js
k6 run validation/k6/chat_spike.js
k6 run validation/k6/chat_soak.js
k6 run validation/k6/ingest_concurrent.js
```

## Pentest checklist

See `validation/pentest/checklist.md`.

