---
sidebar_position: 1
title: 'Swap Database'
description: 'Guide for switching from ChromaDB to PostgreSQL/pgvector'
component_type: 'guide'
layer: 'infrastructure'
ports: ['VectorStorePort']
technologies: ['ChromaDB', 'PostgreSQL', 'pgvector']
---

# Swap Database

This guide explains how to switch the default ChromaDB vector store to PostgreSQL with pgvector, utilizing our Hexagonal Architecture.

## The VectorStorePort Contract

Any vector database must implement this port:

```python
from typing import Protocol, List, Dict, Any, Optional

class VectorStorePort(Protocol):
    def similarity_search(
        self,
        query_text: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        ...
        
    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        ...
        
    def heartbeat(self) -> bool:
        ...
```

## Step-by-Step Migration

1. **Create the Adapter**
Create a new file `app/infrastructure/persistence/postgres_adapter.py` and implement `VectorStorePort`.

2. **Implement Methods**
```python
class PostgresAdapter:
    def similarity_search(self, query_text: str, k: int = 5, filter=None):
        # Implement pgvector search; honor metadata filter when provided
        pass
        
    # implement other methods...
```

3. **Register in Dependency Injection**
Update `app/wiring.py` to inject `PostgresAdapter` instead of `ChromaAdapter`.

4. **Update Environment**
Add the new database credentials to your `.env`:
```env
VECTOR_STORE=postgres
PG_CONNECTION_STRING=postgresql://user:pass@localhost:5432/db
```

> [!WARNING]
> Ensure your Docker Compose stack includes the PostgreSQL container with pgvector extension installed.
