# Evidence Boundary Hardening

## Propósito

Cerrar los riesgos que impiden una beta técnica verificable del nodo documental. El criterio no es que el sistema arranque: debe importar, persistir, reiniciar, recuperar evidencia del documento seleccionado y comunicar cualquier degradación al usuario.

## Cambios comprometidos

1. **Persistencia segura** — El runtime no usará un índice vectorial efímero como fallback. Si Chroma no está disponible, declarará la capacidad degradada y bloqueará la indexación vectorial.
2. **Recuperación** — Se añadirá reindexación desde las fuentes almacenadas por hash; conservará los originales y creará nuevos trabajos durables.
3. **Salud observable** — API y web tendrán healthchecks verificables. Las capacidades expondrán almacenamiento, FTS, vector, inferencia, embeddings, OCR y su estado.
4. **Recibo de evidencia** — La UI mostrará documento, ubicación, extracto, proveedor, decisión y latencia; el fallback extractivo será visible.
5. **Gates reproducibles** — Se añadirá smoke test post-build: imágenes nuevas, compose, healthchecks, importación del PDF autorizado, consulta con evidencia y teardown.
6. **Riesgos de dependencias** — Las vulnerabilidades sin fix se registrarán con fecha, mitigación y responsable de revisión; no se ignorarán silenciosamente en CI.

## Fuera de alcance

- No se borra ni reescribe el runtime legacy; permanece tras `ENABLE_LEGACY_EXTENSIONS`.
- No se introducen proveedores cloud ni se cambian modelos sin una decisión explícita.
- No se usan documentos sintéticos como aceptación de producto o demo.

## Criterio de salida

1. `pytest`, compilación web y lockfile pasan.
2. Una imagen API y una web recién construidas arrancan con healthchecks verdes.
3. Tras importar `zyrabit-cioreview-en.pdf`, una consulta entrega evidencia del documento y página correctos.
4. Tras reiniciar el stack, el mismo documento puede reindexarse y consultarse sin pérdida silenciosa.
5. Una caída de Chroma, embeddings o inferencia aparece como degradación visible, nunca como éxito falso.
