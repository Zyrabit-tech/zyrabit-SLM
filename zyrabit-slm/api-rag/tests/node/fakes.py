from __future__ import annotations


class InMemoryVectorIndex:
    """Contract double: test job readiness without a remote vector service."""
    def __init__(self):
        self.evidence = []

    def upsert(self, evidence):
        self.evidence.extend(evidence)

    def search(self, query, limit=8, document_id=None):
        return []

    def health(self):
        return True, "test-index"
