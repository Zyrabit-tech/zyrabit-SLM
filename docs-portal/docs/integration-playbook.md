# Integration Playbook (ES/EN)

## ES: Preguntas clave y decisiones de arquitectura

### 1) Si mañana agregamos Make, Strapi o una nueva DB, ¿se integra igual que n8n?

Sí. El estándar recomendado es:

1. Definir un `port` de aplicación (contrato).
2. Implementar un `adapter` por proveedor (`MakeAdapter`, `StrapiAdapter`, etc.).
3. Exponer la integración por Traefik en el entrypoint único (`https://localhost`).
4. Aplicar políticas de token, firma y logging.

### 2) ¿Cómo conectamos n8n sin romper la arquitectura hexagonal?

- `n8n` funciona como sistema externo.
- `api-rag` mantiene el dominio y casos de uso.
- El endpoint `POST /v1/integrations/n8n/webhook` usa un adapter dedicado.
- El adapter transforma payload externo a contrato interno (`text` + metadata opcional).

### 3) ¿Qué políticas mínimas de integración usamos?

- `Authorization: Bearer <token>` para autenticación de servicio.
- Firma HMAC SHA-256 en `X-Zyrabit-Signature` para integridad.
- Contrato estable de payload (`text` obligatorio).
- Sin puertos públicos adicionales por integración.
- Secretos por `_FILE` (Docker Secrets) o Vault on-prem en producción.

### 4) ¿Cómo crecer esto sin acoplar todo?

- Un provider nuevo no toca el core: agrega su adapter.
- Reusar el mismo patrón de pruebas: token inválido, firma inválida, payload inválido, payload válido.
- Documentar variables y rutas en README + docs-portal.

### 5) ¿Cómo armamos MakeAdapter?

Ruta de arranque recomendada:

1. Copiar `api-rag/app/adapters/make_adapter_blueprint.py`.
2. Ajustar headers reales de Make (`Authorization`, firma, metadata de escenario).
3. Normalizar payload hacia el contrato interno: `text` + metadata opcional.
4. Añadir endpoint dedicado (`/v1/integrations/make/webhook`) o reusar router de adapters.
5. Agregar pruebas con la matriz de seguridad (token/firma/payload).

### 6) ¿Cómo armamos el Super-Fine-Tuning Pipeline local?

Secuencia mínima:

1. Detectar fallos de respuesta y emitir evento `model_miss_detected`.
2. Guardar ejemplo en dataset local curado (`prompt`, respuesta esperada, dominio técnico).
3. Ejecutar job offline LoRA/PEFT por lote (sin internet).
4. Evaluar contra benchmark local.
5. Promover modelo sólo si supera umbral de calidad y seguridad.

## EN: Key questions and architecture decisions

### 1) If we add Make, Strapi, or a new DB tomorrow, do we integrate it like n8n?

Yes. Recommended standard:

1. Define an application `port` (contract).
2. Implement one provider `adapter` (`MakeAdapter`, `StrapiAdapter`, etc.).
3. Publish through Traefik under a single entrypoint (`https://localhost`).
4. Apply token, signature, and audit policies.

### 2) How do we connect n8n without breaking hexagonal boundaries?

- `n8n` is treated as an external system.
- `api-rag` keeps domain and use-case orchestration.
- `POST /v1/integrations/n8n/webhook` is backed by a dedicated adapter.
- The adapter maps external payloads to a stable internal contract (`text` + optional metadata).

### 3) What are the minimum integration policies?

- `Authorization: Bearer <token>` for service authentication.
- HMAC SHA-256 signature in `X-Zyrabit-Signature` for request integrity.
- Stable payload contract (`text` required).
- No additional public ports per integration.
- Production secrets via `_FILE` (Docker Secrets) or on-prem Vault.

### 4) How does this scale without tight coupling?

- New providers should not modify the core use-cases.
- Reuse the same test matrix: invalid token, invalid signature, invalid payload, valid payload.
- Keep README and docs-portal synchronized for variables, routes, and profile usage.

### 5) How do we build a MakeAdapter?

Recommended bootstrap path:

1. Copy `api-rag/app/adapters/make_adapter_blueprint.py`.
2. Adapt real Make headers (auth, signature, scenario metadata).
3. Normalize external payload into internal contract: `text` + optional metadata.
4. Add a dedicated endpoint (`/v1/integrations/make/webhook`) or route through a shared adapter gateway.
5. Add the same security test matrix (token/signature/payload).

### 6) How do we build a local super-fine-tuning pipeline?

Minimum sequence:

1. Emit `model_miss_detected` when technical responses fail.
2. Persist curated examples locally (`prompt`, expected answer, domain tag).
3. Run offline LoRA/PEFT jobs in batches.
4. Evaluate against a local benchmark.
5. Promote a tuned model only if quality and safety gates pass.
