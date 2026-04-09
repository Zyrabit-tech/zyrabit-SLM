# Zyrabit SLM

[English version](README_EN.md)

Stack backend para RAG local seguro, puente MCP y observabilidad.

> Runtime recomendado local: **Python 3.12** para evitar incompatibilidades con dependencias legacy en Python 3.14+.

## Contenido de esta carpeta

- `api-rag/`: API en FastAPI y flujo de seguridad.
- `docker-compose.yml`: orquestacion local del stack.
- `config/`: provisionamiento de Prometheus y Grafana.
- `traefik/`: configuracion de reverse proxy y reglas de seguridad.

## Capacidades principales

- Anonimizacion de PII basada en interceptores antes de inferencia.
- Desanonimizacion reversible de tokens al responder al usuario.
- Metricas Prometheus en `/metrics`:
  - `zyrabit_token_latency_ms_per_token`
  - `zyrabit_token_usage_total`
  - `zyrabit_security_hits_total`
- Endpoints MCP:
  - `GET /mcp/config.json`
  - `POST /mcp`
- Endpoint de integración n8n (adapter + políticas):
  - `POST /v1/integrations/n8n/webhook`

## Inicio rapido

Desde la raiz del repositorio:

```bash
chmod +x zyra-up.sh
./zyra-up.sh install
```

Scripts principales de instalacion:

- `install.sh`: bootstrap remoto/local para primera ejecucion.
- `zyra-up.sh`: entrada principal para validar entorno y levantar stack.

## Validacion de variables de entorno

El script `zyra-up.sh` valida el valor efectivo de variables requeridas antes de arrancar:

- Prioriza variables del entorno del servidor (por ejemplo CI/CD o systemd).
- Si no existen en runtime, usa `zyrabit-brain-api/.env` como fallback.
- Deben existir y tener valor valido:
  - `SLM_URL`
  - `DB_URL`
  - `MODEL_NAME`
- Se rechazan valores vacios o invalidos como `undefined`, `null`, `none`.

Plantilla completa: copia `example.env` a `.env` y ajusta valores:

```bash
cp example.env .env
```

Ejemplo minimo para `.env` (opcional si ya exportas variables en servidor):

```bash
INFERENCE_PROVIDER=ollama
SLM_URL=http://slm-engine:11434/api/generate
DB_URL=http://vector-db:8000
MODEL_NAME=qwen2.5:7b
INFERENCE_TIMEOUT_SECONDS=120
PROMETHEUS_BASIC_AUTH=admin:$2y$05$...   # htpasswd -nbB admin 'password'
GRAFANA_BASIC_AUTH=admin:$2y$05$...      # idem
```

### Proveedores de inferencia intercambiables (factory + adapters)

La capa de inferencia usa contrato por puerto (`app/ports/inference_port.py`) con factory (`app/inference_factory.py`) y adapters:

- `ollama` / `ollama_host` / `ollama_docker` -> `SLM_URL=/api/generate`
- `openai_compatible` -> `INFERENCE_BASE_URL=/v1/chat/completions`

Ejemplo modo hibrido (Ollama nativo host + resto en Docker):

```bash
INFERENCE_PROVIDER=ollama_host
SLM_URL=http://host.docker.internal:11434/api/generate
MODEL_NAME=qwen2.5:7b
```

Variables para integracion n8n (adapter webhook):

```bash
N8N_SERVICE_TOKEN=replace-with-strong-token
N8N_WEBHOOK_SIGNING_SECRET=replace-with-hmac-secret
N8N_REQUIRE_SIGNATURE=true
```

En produccion, usa secretos por archivo o Vault (no hardcode):

```bash
N8N_SERVICE_TOKEN_FILE=/run/secrets/n8n_service_token
N8N_WEBHOOK_SIGNING_SECRET_FILE=/run/secrets/n8n_webhook_signing_secret
```

Credenciales de autenticacion basica para observabilidad en Traefik:

```bash
PROMETHEUS_BASIC_AUTH=<usuario:hash_htpasswd>
GRAFANA_BASIC_AUTH=<usuario:hash_htpasswd>
```

Ejemplo para generar hash:

```bash
htpasswd -nbB admin 'cambia-esto'
```

## Ejemplos de uso

Verificar entorno y configuracion:

```bash
./zyra-up.sh doctor
```

Levantar infraestructura:

```bash
./zyra-up.sh start
```

Levantar stack manualmente con Docker Compose:

```bash
cd zyrabit-brain-api
docker compose up -d
```

Levantar e instalar modelos base:

```bash
./zyra-up.sh install
```

Descargar modelos manualmente (sin flujo automático):

```bash
docker compose exec -T slm-engine ollama pull qwen2.5:7b
docker compose exec -T slm-engine ollama pull mxbai-embed-large
```

Consultar salud de la API:

```bash
curl -k https://localhost/health
```

Enviar una consulta al router:

```bash
curl -k https://localhost/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"Explica la arquitectura de Zyrabit"}'
```

Respuesta de `POST /v1/chat`:

```json
{
  "response": "...",
  "metadata": {
    "route_decision": "search_rag_database",
    "rag_hits": 2,
    "latency_ms": 305.44
  }
}
```

Ingestar documento:

```bash
curl -k -X POST https://localhost/v1/ingest \
  -F "file=@api-rag/sample_docs/zyrabit_project_overview.txt"
```

Respuesta de `POST /v1/ingest`:

```json
{
  "status": "success",
  "filename": "zyrabit_project_overview.txt",
  "chunks_processed": 4,
  "message": "Documento ingestado correctamente en la base de conocimiento.",
  "ingest_id": "..."
}
```

Ver ejemplos completos: `docs/CURL_EXAMPLES.md` y workflow n8n en `docs/n8n_zyrabit_webhook_workflow.json`.

Enviar evento desde n8n al adapter:

```bash
curl -k https://localhost/v1/integrations/n8n/webhook \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${N8N_SERVICE_TOKEN}" \
  -H "X-Zyrabit-Signature: sha256=<hmac_sha256_del_body>" \
  -d '{"text":"Resume estado de observabilidad","workflow_id":"wf-001","execution_id":"exec-001"}'
```

## Capas de abstraccion

La solucion esta organizada por capas para separar responsabilidades:

1. **Capa de entrada (Edge/Ingress)**
   - `traefik` recibe trafico y aplica TLS, redirecciones y rate limiting.
2. **Capa de aplicacion**
   - `api-rag` expone endpoints HTTP y coordina la logica.
3. **Capa de seguridad**
   - Pipeline de anonymizacion/desanonimizacion de datos sensibles.
4. **Capa de inferencia**
   - `slm-engine` (Ollama) ejecuta el modelo local.
5. **Capa de conocimiento**
   - `vector-db` almacena y recupera embeddings/contexto.
6. **Capa de observabilidad**
   - `prometheus`, `grafana` y opcionalmente `loki`.

## Patrones aplicados

- **Interceptor Pipeline**: cadena de transformaciones para sanitizar input/output.
- **Router Pattern**: el endpoint `/v1/chat` decide entre flujo RAG o respuesta directa.
- **Facade/API Gateway**: FastAPI y Traefik simplifican acceso al sistema distribuido.
- **Defense in Depth**: redes segmentadas + sanitizacion + reverse proxy.

## Arquitectura utilizada

- **Arquitectura por servicios (micro-servicios locales)** orquestada con Docker Compose.
- **Estilo Clean / Layered** dentro de `api-rag` para aislar transporte, servicios y seguridad.
- **Topologia Zero-Trust local**: nada de datos sensibles sale fuera de la infraestructura.

## Topologia de servicios

- `traefik`: ingress, HTTPS y politicas de entrada.
- `api-rag`: nucleo FastAPI.
- `slm-engine`: motor de inferencia local.
- `vector-db`: capa de persistencia semantica.
- `prometheus` + `grafana`: monitoreo.
- `loki` (perfil opcional): logs centralizados.
- `docs-portal` (perfil opcional): portal de documentacion.
- `n8n` (perfil opcional `automation`): automatizacion por webhook, publicado via Traefik (`/n8n`).

Redes:

- `frontend-network`
- `backend-network`
- `model-network` (`internal: true`)

## Manejo de Entorno (Managed Environment)

> [!TIP]
> Para evitar errores de "module not found" (como `pytest`), se recomienda encarecidamente trabajar dentro de un entorno virtual.

1. **Crear el entorno virtual:**
   ```bash
   python3 -m venv .venv
   ```

2. **Activarlos:**
   - macOS / Linux: `source .venv/bin/activate`
   - Windows: `.\.venv\Scripts\activate`

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   pip install -r api-rag/requirements.txt
   ```

## Testing

Asegúrate de tener el entorno activado antes de correr los tests.

```bash
cd api-rag
python3 -m pytest -q
```

Suites clave:

- `tests/test_security.py`: comportamiento de sanitizacion PII.
- `tests/test_services_security.py`: evita fuga de PII al payload del modelo.
- `tests/test_integration.py`: integracion API.
- `tests/test_mcp.py`: contrato MCP y sanitizacion.

## Referencias de seguridad

- Politica global: `../SECURITY.md`
- Config MCP estatico: `../mcp/config.json`

## Politicas de integracion (n8n y futuros adapters)

- **Single entrypoint**: todo acceso externo por Traefik (`https://localhost`), sin puertos publicos adicionales por servicio.
- **Token de servicio**: `Authorization: Bearer <token>` obligatorio para adapters de automatizacion.
- **Integridad de webhook**: firma HMAC SHA-256 en `X-Zyrabit-Signature` cuando `N8N_REQUIRE_SIGNATURE=true`.
- **Contrato estable**: payload minimo `{ "text": "..." }`; metadatos opcionales `workflow_id`, `execution_id`.
- **Arquitectura hexagonal**: nuevas integraciones (Make, Strapi, DB connectors) deben implementar su propio adapter sobre un port, sin acoplar el dominio a proveedores externos.
- **Secrets en produccion**: usar `_FILE` con Docker Secrets o un Vault on-prem, nunca secretos en claro en `docker-compose.yml`.

## Observabilidad sin puertos publicos

- `grafana` se publica por `https://localhost/grafana`.
- `prometheus` se publica por `https://localhost/prometheus`.
- Ambos quedan detras de Traefik con middleware `basicauth` configurable por variables de entorno.

## Plantilla para nuevos adapters (Make)

Se incluye plantilla base en:

- `api-rag/app/adapters/make_adapter_blueprint.py`

La plantilla implementa el mismo contrato del `AutomationPort` y sirve como referencia para:

- validacion de token
- validacion de firma HMAC
- normalizacion de payload externo a contrato interno estable
