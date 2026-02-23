# Zyrabit Brain API

[English version](README_EN.md)

Stack backend para RAG local seguro, puente MCP y observabilidad.

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

Ejemplo minimo para `.env` (opcional si ya exportas variables en servidor):

```bash
SLM_URL=http://slm-engine:11434/api/generate
DB_URL=http://vector-db:8000
MODEL_NAME=qwen2.5:7b
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

Levantar e instalar modelos base:

```bash
./zyra-up.sh install
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

Redes:

- `frontend-network`
- `backend-network`
- `model-network` (`internal: true`)

## Testing

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
