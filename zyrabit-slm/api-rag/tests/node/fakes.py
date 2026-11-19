from __future__ import annotations

from typing import Any, Dict, List, Optional

# ==============================================================================
# TEST DOUBLE RATIONALE (IN-MEMORY VECTOR INDEX CONTRACT DOUBLE)
# ==============================================================================
# Purpose: Simulate in-memory vector storage to validate ingestion flow,
# scope isolation, and Node API contracts.
# Rationale:
# Validates indexing logic and evidence extraction without depending on an
# active ChromaDB server or writing temporary files to disk.
# Signatures must match VectorIndex / VectorStorePort so filter regressions
# surface as TypeError in tests instead of being silently swallowed.
# ==============================================================================


class InMemoryVectorIndex:
    """Contract double: test job readiness without a remote vector service."""

    def __init__(self):
        self.evidence = []

    def upsert(self, evidence):
        self.evidence.extend(evidence)

    def search(self, query: str, limit: int = 8, document_id: str | None = None):
        # Intentionally empty: lexical path remains the primary signal in Node
        # acceptance tests. Signature still matches VectorIndex so unexpected
        # kwargs fail loudly instead of being swallowed upstream.
        _ = (query, limit, document_id)
        return []

    def delete(self, document_id: str) -> None:
        self.evidence = [e for e in self.evidence if getattr(e, "document_id", None) != document_id]

    def health(self) -> tuple[bool, str]:
        return True, "test-index"


class RecordingVectorStore:
    """Strict VectorStorePort double: rejects unknown kwargs like a real adapter."""

    def __init__(self):
        self.calls: list[dict[str, Any]] = []
        self.documents: list[Any] = []

    def similarity_search(
        self,
        query_text: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        self.calls.append({"query_text": query_text, "k": k, "filter": filter})
        results = self.documents
        if filter:
            results = [
                doc
                for doc in results
                if all(getattr(doc, "metadata", {}).get(key) == value for key, value in filter.items())
            ]
        return results[:k]

    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        pass

    def add_documents(self, documents: List[Any]) -> None:
        self.documents.extend(documents)

    def delete(self, where: Dict[str, Any]) -> None:
        document_id = where.get("document_id")
        if document_id is None:
            return
        self.documents = [
            doc for doc in self.documents if getattr(doc, "metadata", {}).get("document_id") != document_id
        ]

    def heartbeat(self) -> bool:
        return True
