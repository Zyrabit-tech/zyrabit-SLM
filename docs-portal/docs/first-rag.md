# Your First RAG Query

To execute your first Retrieval-Augmented Generation (RAG) query, follow these steps:

1. **Start the stack:** Run `./zyra-up.sh`.
2. **Ingest documents:** Upload files via the `/v1/ingest` endpoint.
3. **Submit a query:** Send a POST request to the `/v1/chat` endpoint.

### Example Request

```bash
curl -k -X POST https://localhost/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -d '{"text":"What is the summary of the policy we just ingested?"}'
```
