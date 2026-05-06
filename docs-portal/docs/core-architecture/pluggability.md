# Pluggable Architecture: Swapping Components

Zyrabit SLM is built on a **Hexagonal Architecture** (Ports and Adapters). This design pattern ensures that the core logic—the `api-rag`—is completely decoupled from infrastructure dependencies. 

You can swap your inference engine (e.g., from Ollama to Anthropic) or your vector database (e.g., from ChromaDB to Postgres + pgvector) without modifying the application core.

---

## 1. Swapping LLM Providers (Inference)

The system uses an **Inference Port** to communicate with language models. To use an external API like OpenAI or Anthropic instead of a local Ollama instance, you must implement or configure a new adapter.

### Supported Adapters
- **Ollama (Default):** Local, sovereign inference.
- **Gemini:** Google's generative AI API.

### Adding a New Provider (e.g., Anthropic/OpenAI)
To integrate a new provider:
1. **Implement the Adapter:** Create a new file in `app/infrastructure/inference/` (e.g., `anthropic_adapter.py`) implementing the `InferenceProviderPort`.
2. **Update the Factory:** Register the new adapter in `app/inference_factory.py`.
3. **Configure Environment:** Set the `INFERENCE_PROVIDER` variable in your `.env` file.

```env
# Example: Switching to a cloud provider
INFERENCE_PROVIDER="anthropic"
ANTHROPIC_API_KEY="sk-ant-..."
```

---

## 2. Swapping Vector Databases (Persistence)

The RAG engine interacts with the vector database through a **Persistence Port**. While Zyrabit ships with ChromaDB as the default for its simplicity and local-first nature, it can be replaced with enterprise-grade solutions like Postgres with `pgvector`.

### Migration to Postgres + `pgvector`
To swap the vector store:
1. **Add the Postgres Adapter:** Implement the `VectorStorePort` in a new `app/infrastructure/persistence/postgres_adapter.py`.
2. **Database Dependencies:** Ensure the `postgres` service is added to your `docker-compose.yml` with the `pgvector` extension enabled.
3. **Update Dependency Injection:** Configure the system to inject the `PostgresAdapter` instead of the `ChromaAdapter` in the infrastructure layer.

---

## 3. Benefits of Hexagonal Design

- **Technology Independence:** Swap components as the AI landscape evolves.
- **Testability:** Mock external providers easily for unit and integration testing.
- **Data Sovereignty Flexibility:** Switch between 100% local stacks (Ollama + Chroma) and hybrid stacks (OpenAI + Local DB) depending on your organization's privacy requirements.
