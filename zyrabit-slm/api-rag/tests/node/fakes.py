from __future__ import annotations

# ==============================================================================
# JUSTIFICACIÓN DE TEST DOUBLE (IN-MEMORY VECTOR INDEX CONTRACT DOUBLE)
# ==============================================================================
# Propósito: Simular almacenamiento de vectores en memoria para validar el flujo
# de ingesta, aislamiento de scopes y contratos de la API Node.
# Justificación:
# Permite validar la lógica de índices y extracción de evidencias sin depender
# de un servidor ChromaDB activo ni escribir archivos temporales en disco.
# ==============================================================================


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
