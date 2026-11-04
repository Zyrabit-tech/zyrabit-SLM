from __future__ import annotations

# ==============================================================================
# TEST DOUBLE RATIONALE (IN-MEMORY VECTOR INDEX CONTRACT DOUBLE)
# ==============================================================================
# Purpose: Simulate in-memory vector storage to validate ingestion flow,
# scope isolation, and Node API contracts.
# Rationale:
# Validates indexing logic and evidence extraction without depending on an
# active ChromaDB server or writing temporary files to disk.
# ==============================================================================


class InMemoryVectorIndex:
    """Contract double: test job readiness without a remote vector service."""
    def __init__(self):
        self.evidence = []

    def upsert(self, evidence):
        self.evidence.extend(evidence)

    def search(self, query, limit=8, document_id=None):
        return []

    def delete(self, document_id):
        self.evidence = [e for e in self.evidence if getattr(e, "document_id", None) != document_id]

    def health(self):
        return True, "test-index"
