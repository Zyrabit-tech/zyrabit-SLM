# Data Portability & Exit Strategy

Zyrabit SLM is designed with a commitment to data sovereignty and transparency. We ensure that your organization retains full control over its data, with a clear path to export or migrate your information without vendor lock-in.

## Data Storage Locations

By default, Zyrabit persists data in the following host directories (mapped via Docker volumes):

| Data Type | Container Path | Host Default Path (Relative) | Format |
| :--- | :--- | :--- | :--- |
| **Vector Database** | `/var/lib/chroma` | `./data/vector-db` | SQLite / Parquet |
| **Models** | `/root/.ollama` | `./data/models` | GGUF |
| **Telemetry** | `/var/lib/prometheus` | `./data/prometheus` | TSDB |
| **Logs** | `/var/log/zyrabit` | `./logs` | JSON / Plain Text |

## Exporting Vector Data

Zyrabit utilizes **ChromaDB** for vector storage. To export your collection metadata and document mappings, you can interface directly with the persistent SQLite database or use our CLI utility:

```bash
# Export collection to Parquet format
docker exec -it zyrabit-api python scripts/export_vectors.py --output /tmp/export.parquet
```

## Model Portability

All Small Language Models (SLMs) managed by Zyrabit are stored in the industry-standard **GGUF** format. These models can be moved to any other system running Ollama, llama.cpp, or compatible runtimes without modification.

## Logs & Audit Trails

Inference logs and security hits are written in structured JSON format. This allows for seamless ingestion into enterprise SIEM or log management systems (e.g., ELK Stack, Splunk) via standard log forwarders.

## Exit Procedure

If you decide to decommission Zyrabit SLM:
1. **Stop the stack:** `docker compose down`.
2. **Backup the data directory:** `tar -czvf backup.tar.gz ./data`.
3. **Delete volumes (Optional):** `docker volume prune`.

Your datasets remain in open, non-proprietary formats, ensuring they can be repurposed in any other RAG or AI orchestration framework.
