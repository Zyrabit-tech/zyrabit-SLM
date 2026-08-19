# cURL Examples — Zyrabit Brain API

Base URL: `https://localhost` (use `-k` to ignore self-signed certificates)

---

## Prometheus / Grafana Credentials

`PROMETHEUS_BASIC_AUTH` and `GRAFANA_BASIC_AUTH` in `.env` contain a **hash** (not plaintext). The hash in `example.env` corresponds to:

- **Username:** `admin`
- **Password:** `changeme`

**No need to generate new credentials.** Use `admin` / `changeme` to access:
- https://localhost/prometheus
- https://localhost/grafana

To change the password: `htpasswd -nbB admin 'your-password'` and update `.env`.

---

## Health Check

```bash
curl -k https://localhost/health
```

---

## Chat (RAG or direct SLM)

```bash
# Query using RAG (keywords: zyrabit, architecture, etc.)
curl -k -X POST https://localhost/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"What is Zyrabit and how is its architecture designed?"}'

# General query (routes directly to SLM)
curl -k -X POST https://localhost/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"What is Python?"}'
```

---

## Ingest Document

```bash
# PDF
curl -k -X POST https://localhost/v1/ingest \
  -F "file=@/path/to/document.pdf"

# TXT or MD
curl -k -X POST https://localhost/v1/ingest \
  -F "file=@/path/to/document.txt"
```

---

## n8n Webhook

Requires `Authorization: Bearer <N8N_SERVICE_TOKEN>` from `.env`. When `N8N_REQUIRE_SIGNATURE=false`, signatures are not required.

```bash
export N8N_TOKEN="zyrabit-service-token"   # default value in example.env

curl -k -X POST https://localhost/v1/integrations/n8n/webhook \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $N8N_TOKEN" \
  -d '{"text":"Summarize the state of Zyrabit"}'
```

### n8n Workflow

Import `docs/n8n_zyrabit_webhook_workflow.json` into n8n (Import from File). Workflow design:
- Manual Trigger → HTTP Request to Zyrabit
- URL: `https://host.docker.internal/...` (if n8n runs in Docker) or `https://localhost/...` (if n8n runs on host)
- Header `Authorization: Bearer zyrabit-service-token` (must match `N8N_SERVICE_TOKEN` in `.env`)

Start n8n: `docker compose --profile automation up -d n8n`

---

## Prometheus (Basic Auth)

```bash
curl -k -u admin:changeme https://localhost/prometheus/-/healthy
```

---

## Grafana (Basic Auth)

```bash
curl -k -u admin:changeme https://localhost/grafana/api/health
```
