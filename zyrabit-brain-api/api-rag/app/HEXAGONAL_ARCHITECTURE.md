# Zyrabit Hexagonal Architecture (Sovereign Pattern)

This project follows a strict **Hexagonal Architecture** (also known as Ports and Adapters) to ensure that the core logic is isolated from external dependencies like databases, LLM engines, and delivery protocols.

## Layer Overview

### 1. Domain Layer (`app/domain/`)
- **Entities**: Core data models (if any).
- **Use Cases**: Orchestration logic (e.g., `ChatUseCase`, `IngestUseCase`).
- **Domain Services**: Logic that doesn't belong to a single entity, like the **Gatekeeper**.

### 2. Port Layer (`app/ports/`)
- **Interfaces**: Abstract definitions of what the system needs from the outside world.
    - `InferenceProviderPort`: Contract for LLM interaction.
    - `VectorStorePort`: Contract for knowledge storage.

### 3. Adapter Layer (`app/adapters/` -> migrating to `api/` & `infrastructure/`)
- **Driving Adapters (Primary)**: The triggers for our system.
    - `api/v1/`: FastAPI REST endpoints.
    - Socket.io handlers in `main.py`.
- **Driven Adapters (Secondary)**: Implementations of the ports.
    - `infrastructure/persistence/`: ChromaDB implementation.
    - `infrastructure/inference/`: Ollama implementation.

### 4. Core Layer (`app/core/`)
- **Security**: PII Pipeline, sanitization.
- **Diagnostics**: Health checks, metrics, and logs.
- **Config**: Environment settings.

## Data Flow
1. A request enters through an **API Adapter** (REST or Socket).
2. The adapter invokes a **Use Case** in the **Domain Layer**.
3. The Use Case asks the **Gatekeeper** (Domain Service) for a routing decision.
4. If approved, the Use Case communicates with the **Infrastructure Adapters** via their **Ports**.
5. The result is returned to the original adapter and sent to the user.
