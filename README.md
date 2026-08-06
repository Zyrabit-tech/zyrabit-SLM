# Zyrabit SLM

Local document-analysis workspace. It indexes files into a Chroma collection, retrieves relevant chunks for each prompt, and calls a configurable inference provider. The browser UI, API, vector store, and document volume run on the same Docker network.

## Local run

Requirements: Docker Desktop and a local inference provider. The default provider is Ollama at `http://localhost:11434`.

```bash
git clone https://github.com/Zyrabit-tech/zyrabit-SLM.git
cd zyrabit-SLM
cp zyrabit-slm/example.env zyrabit-slm/.env
# Set distinct random values for ZYRABIT_API_KEY_WEB and ZYRABIT_API_KEY_MCP.
./zyra.sh install
```

Open `http://localhost:8080`. This is the only host port in the local profile. The UI proxies `/v1`, `/mcp`, and `/socket.io` to the API; Chroma is private to Docker.

Useful commands:

```bash
./zyra.sh start       # start existing containers
./zyra.sh verify      # inspect container and API health
./zyra.sh stop        # stop the local stack
./zyra.sh dev         # run the API with reload, without Docker
```

## System layout

```text
browser ── http://localhost:8080 ──> nginx UI ──> FastAPI
                                                    ├── Chroma (vector search)
                                                    ├── SQLite WAL (profiles and session state)
                                                    ├── local files (/document_source)
                                                    ├── local inference provider
                                                    └── MCP bridge
```

The API starts even if Chroma is unavailable: it uses an ephemeral Chroma client for that process. This permits standalone development but does not preserve indexed documents across restarts.

## Capabilities

- Upload and index PDF, DOCX, text, and supported audio files; audio is transcribed before ingestion.
- Hybrid retrieval with vector search and a BM25 in-memory index.
- Session memory backed by SQLite WAL.
- HTTP, Socket.IO, and AG-UI chat endpoints.
- MCP tool discovery and JSON-RPC bridge at `/mcp`.
- Pluggable Ollama, MLX, llama.cpp, vLLM, and compatible inference adapters.

## Configuration

Copy `zyrabit-slm/example.env` to `.env`. The important local fields are:

| Variable | Purpose |
| --- | --- |
| `ZYRABIT_LOCAL_PORT` | Browser entrypoint; defaults to `8080`. |
| `ZYRABIT_API_KEY_WEB` | Browser-to-API bearer key, injected into the UI container at startup. |
| `ZYRABIT_API_KEY_MCP` | Key for MCP/API clients. |
| `SLM_URL` | Inference endpoint; defaults to the host Ollama endpoint in Docker. |
| `MODEL_NAME` | Chat model name. |
| `EMBEDDING_MODEL` | Ollama embedding model used while indexing. |
| `DOCS_DIR` | Document directory inside the API container. |

Do not commit `.env`. The UI token is intentionally supplied at container startup rather than stored in JavaScript source. It is still visible to a user of the local browser session, so production deployments must place authentication at an external gateway and use a separate deployment configuration.

## API and MCP

All API routes require `Authorization: Bearer <key>` except the health route.

```bash
curl http://localhost:8080/v1/health
curl -X POST http://localhost:8080/v1/chat \
  -H "Authorization: Bearer $ZYRABIT_API_KEY_MCP" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Summarize the uploaded documents"}'
```

For MCP discovery and connection examples, see [MCP integration](mcp/README.md). The full component and operational contract is in [Technical reference](docs/TECHNICAL_REFERENCE.md).

## Validation

```bash
pytest -q zyrabit-slm/api-rag/tests/unit
pnpm --dir zyrabit-slm/web-ui build
docker compose -f zyrabit-slm/docker-compose.local.yml config
```

Python tests require the project dependencies (`uv sync --all-groups` or an equivalent environment) before running.

## Repository map

```text
zyrabit-slm/api-rag/   FastAPI application, domain logic, adapters, tests
zyrabit-slm/web-ui/    Vite/Tailwind document workspace
zyrabit-slm/           Docker profiles and runtime configuration
mcp/                   Standalone MCP installer/diagnostic server
docs/                  Engineering documentation
validation/            Load and operational test assets
internal/              Hardware-specific integrations
```

## License

MIT. See [LICENSE](LICENSE).
