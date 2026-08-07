# Zyrabit Node: arquitectura técnica

## Objetivo

Un nodo local recibe documentos, conserva su original, genera unidades de evidencia y responde sólo con evidencia indexada. El núcleo no arranca conectores externos ni agentes.

## Flujo

```
POST /v1/sources/import
  → almacenamiento local por SHA-256
  → job SQLite (queued → extracting → persisting_evidence → indexing_vectors → ready)
  → parser local → evidence units + FTS5 + índice vectorial opcional
POST /v1/query
  → FTS5 + vector search opcional → evidencia → proveedor local → respuesta + fuentes
```

SQLite conserva fuentes, versiones documentales, trabajos, evidencia, FTS, sesiones, capacidades y eventos. Los archivos se almacenan por hash bajo `NODE_DATA_DIR/sources`; no se sobrescriben por nombre.

## Puertos

El dominio `app/node` define contratos para origen, parser, OCR, metadatos, vector index, embeddings, reranking e inferencia. Los adaptadores actuales son almacenamiento local, SQLite/FTS5, parser local, Chroma y las familias de inferencia existentes. Ollama y llama.cpp se configuran por ambiente; `SLM_URL` y `EMBEDDING_URL` son rutas separadas.

## Formatos

PDF conserva página; DOCX párrafos y tablas; CSV/XLSX hoja y rango; PPTX diapositiva y notas. OCR con Tesseract se habilita sólo con `NODE_ENABLE_OCR=true` y sólo cuando una página PDF no tiene texto nativo.

## Extensiones

MCP, Telegram, Obsidian, AutoLearner y auto-ingesta se preservan. Sólo arrancan al definir `ENABLE_LEGACY_EXTENSIONS=true`. Whisper permanece disponible como herramienta opcional de transcripción en su endpoint existente.

## Operación local

1. Configurar `INFERENCE_PROVIDER`, `SLM_URL`, `EMBEDDING_URL`, `MODEL_NAME` y `EMBEDDING_MODEL` en `zyrabit-slm/.env`.
2. Ejecutar `./zyra.sh install` o `./zyra.sh start`.
3. Consultar `GET /v1/health/capabilities`.
4. Importar a `POST /v1/sources/import` y esperar `GET /v1/jobs/{job_id}` con estado `ready`.

El endpoint legado `POST /v1/ingest` queda soportado, pero ahora devuelve un trabajo durable y no afirma que un documento está listo antes de indexarse.
