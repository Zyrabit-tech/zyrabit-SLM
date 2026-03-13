# Ejemplos cURL - Zyrabit Brain API

Base URL: `https://localhost` (usa `-k` para ignorar certificado self-signed)

---

## Credenciales Prometheus / Grafana

Las variables `PROMETHEUS_BASIC_AUTH` y `GRAFANA_BASIC_AUTH` en `.env` contienen un **hash** (no la contraseña en texto plano). El hash en `example.env` corresponde a:

- **Usuario:** `admin`
- **Contraseña:** `changeme`

**No hace falta generar nuevas.** Usa `admin` / `changeme` para acceder a:
- https://localhost/prometheus
- https://localhost/grafana

Si quieres otra contraseña: `htpasswd -nbB admin 'tu-password'` y reemplaza el valor en `.env`.

---

## Health

```bash
curl -k https://localhost/health
```

---

## Chat (RAG o SLM directo)

```bash
# Pregunta que usa RAG (keywords: zyrabit, architecture, etc.)
curl -k -X POST https://localhost/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"¿Qué es Zyrabit y cuál es su arquitectura?"}'

# Pregunta general (va directo al SLM)
curl -k -X POST https://localhost/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"¿Qué es Python?"}'
```

---

## Ingestar documento

```bash
# PDF
curl -k -X POST https://localhost/v1/ingest \
  -F "file=@/ruta/a/documento.pdf"

# TXT o MD
curl -k -X POST https://localhost/v1/ingest \
  -F "file=@/ruta/a/documento.txt"
```

---

## Webhook n8n

Requiere `Authorization: Bearer <N8N_SERVICE_TOKEN>` del `.env`. Con `N8N_REQUIRE_SIGNATURE=false` no hace falta firma.

```bash
export N8N_TOKEN="zyrabit-service-token"   # valor por defecto en example.env

curl -k -X POST https://localhost/v1/integrations/n8n/webhook \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $N8N_TOKEN" \
  -d '{"text":"Resume el estado de Zyrabit"}'
```

### Workflow n8n

Importa `docs/n8n_zyrabit_webhook_workflow.json` en n8n (Import from File). El workflow:
- Manual Trigger → HTTP Request a Zyrabit
- URL: `https://host.docker.internal/...` (si n8n corre en Docker) o `https://localhost/...` (si n8n corre en el host)
- Header `Authorization: Bearer zyrabit-service-token` (debe coincidir con `N8N_SERVICE_TOKEN` en `.env`)

Levanta n8n: `docker compose --profile automation up -d n8n`

---

## Prometheus (con Basic Auth)

```bash
curl -k -u admin:changeme https://localhost/prometheus/-/healthy
```

---

## Grafana (con Basic Auth)

```bash
curl -k -u admin:changeme https://localhost/grafana/api/health
```
