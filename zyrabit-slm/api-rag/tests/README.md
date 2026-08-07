# Estrategia de pruebas del nodo

La suite principal se ejecuta con `PYTHONPATH=zyrabit-slm/api-rag .venv/bin/python -m pytest`.

| Grupo | Propósito | Criterio |
| --- | --- | --- |
| `tests/node` | Ingesta, trabajos, FTS, aislamiento de documento y respuestas citadas | Bloquea entrega |
| Seguridad e inferencia | Autenticación, PII y contratos de proveedores | Bloquea entrega |
| `tests/legacy` | MCP, ReAct, n8n, chat/cache anterior y script de ingesta previo | Preservado, no ejecutado |

Los tests de aceptación documental usan `api-rag/docs/zyrabit-cioreview-en.pdf` y el Playbook Prospeo que ya vive en `document_source`. No se consideran evidencia de producto los mocks de modelos ni documentos fabricados.

Antes de una demo se ejecuta la suite principal y, con Docker levantado, el flujo físico: importar → `ready` → seleccionar → consultar → revisar extracto y página de la fuente.
