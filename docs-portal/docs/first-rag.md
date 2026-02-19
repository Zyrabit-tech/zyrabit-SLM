# Your First RAG Query

1. Start the stack with `./zyra-up.sh`.
2. Ingest your files via `/v1/ingest`.
3. Query the API via `/v1/chat`.

```bash
curl -k -X POST https://localhost/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"What did we ingest about our policy?"}'
```
