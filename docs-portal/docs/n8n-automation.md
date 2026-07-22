---
sidebar_position: 5
title: 'n8n Workflow Automation'
description: 'Orchestrate AI pipelines using n8n as a workflow automation layer connected to the Zyrabit inference API.'
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# n8n Workflow Automation

Zyrabit ships an optional **automation profile** that runs [n8n](https://n8n.io/) as a self-hosted workflow orchestration engine. n8n can connect Zyrabit's inference and ingestion APIs to external systems — CRMs, document stores, ticketing platforms, and more — without any custom application code, while keeping all data inside your sovereign deployment.

---

## Architecture Overview

```
External System                  Zyrabit Stack (Docker)
──────────────────               ──────────────────────────────────────────
 HubSpot / Pipedrive             ┌──────────────────────────────────────┐
 Shared folder watch     ──────► │  zyrabit-n8n  (n8nio/n8n:1.50.0)    │
 Webhook trigger                 │  port 5678  →  Traefik /n8n          │
                                 └────────────┬─────────────────────────┘
                                              │ HTTP (zyrabit-sovereign-net)
                                 ┌────────────▼─────────────────────────┐
                                 │  api-rag                             │
                                 │  POST /v1/integrations/n8n/webhook   │
                                 │  POST /v1/ingest                     │
                                 └──────────────────────────────────────┘
```

n8n runs inside the `zyrabit-sovereign-net` Docker network and communicates with `api-rag` over the internal network. All traffic originating from external systems is terminated at Traefik.

---

## 1. Enabling the Automation Profile

n8n is declared under the `automation` Docker Compose profile and is **not started** by default. This keeps the base Zyrabit stack lean for deployments that do not require workflow automation.

### Starting with the Automation Profile

```bash
./zyra-up.sh start --profile automation
```

To stop only the automation stack without affecting other services:

```bash
./zyra-up.sh stop --profile automation
```

### Service Definition Reference

The following is the canonical service definition for `zyrabit-n8n`:

```yaml
zyrabit-n8n:
  image: n8nio/n8n:1.50.0
  container_name: zyrabit-n8n
  profiles: [ "automation" ]
  environment:
    - N8N_HOST=localhost
    - N8N_PORT=5678
    - N8N_PROTOCOL=https
    - N8N_PATH=/n8n
    - WEBHOOK_URL=https://localhost/n8n/
    - N8N_SECURE_COOKIE=false
  labels:
    - traefik.enable=true
    - traefik.http.routers.zyrabit-n8n.rule=PathPrefix(`/n8n`)
    - traefik.http.routers.zyrabit-n8n.entrypoints=websecure
    - traefik.http.routers.zyrabit-n8n.tls=true
    - traefik.http.services.zyrabit-n8n.loadbalancer.server.port=5678
  volumes:
    - ./n8n-data:/home/node/.n8n
  networks:
    - zyrabit-sovereign-net
```

**Key configuration notes:**

| Variable | Value | Purpose |
|---|---|---|
| `N8N_HOST` | `localhost` | Hostname n8n reports for itself |
| `N8N_PORT` | `5678` | Internal container port |
| `N8N_PROTOCOL` | `https` | Forces HTTPS scheme in generated URLs |
| `N8N_PATH` | `/n8n` | Sub-path under which n8n is mounted |
| `WEBHOOK_URL` | `https://localhost/n8n/` | Base URL used in n8n webhook registrations |
| `N8N_SECURE_COOKIE` | `false` | Disables secure-only cookie flag for local TLS |

Workflow data is persisted to the `./n8n-data` host volume, mapped to `/home/node/.n8n` inside the container.

---

## 2. Accessing the n8n UI

Once the automation profile is running, the n8n editor is available at:

```
https://localhost/n8n
```

On first access, n8n will prompt you to create an owner account (email and password). This account is local to your deployment and is not connected to any external identity provider.

:::note
Because Zyrabit uses a self-signed TLS certificate by default, your browser will present a certificate warning. Accept the exception to proceed. For production deployments, replace the certificate with one issued by a trusted CA.
:::

---

## 3. Environment Variables and Secrets

### `.env` / `example.env` Configuration

The following variables control how `api-rag` authenticates and validates requests from n8n:

```env
# n8n Integration
N8N_SERVICE_TOKEN=zyrabit-service-token
N8N_WEBHOOK_SIGNING_SECRET=zyrabit-webhook-secret
N8N_REQUIRE_SIGNATURE=false
```

| Variable | Description |
|---|---|
| `N8N_SERVICE_TOKEN` | Bearer token that n8n must present in `Authorization` headers when calling Zyrabit API endpoints. |
| `N8N_WEBHOOK_SIGNING_SECRET` | Shared secret used to generate and verify HMAC SHA-256 request signatures. |
| `N8N_REQUIRE_SIGNATURE` | When `true`, `api-rag` rejects any request from n8n that does not include a valid `X-Zyrabit-Signature` header. When `false`, the signature header is optional. |

### Docker Secrets (Production)

In production deployments, sensitive values should be injected via Docker Secrets rather than plain environment variables. The `api-rag` service supports the following secret file paths:

| Secret File Variable | Mounted Path |
|---|---|
| `N8N_SERVICE_TOKEN_FILE` | Path to a file containing the bearer token |
| `N8N_WEBHOOK_SIGNING_SECRET_FILE` | Path to a file containing the HMAC signing secret |

:::caution
Do not commit real token values to your `.env` file in version control. Rotate `N8N_SERVICE_TOKEN` and `N8N_WEBHOOK_SIGNING_SECRET` before any production deployment and store them using your secrets management solution (Docker Secrets, Vault, etc.).
:::

---

## 4. Zyrabit API Endpoints for n8n

### 4.1 Inference Webhook

| Property | Value |
|---|---|
| **Method** | `POST` |
| **Path** | `/v1/integrations/n8n/webhook` |
| **Auth header** | `Authorization: Bearer <N8N_SERVICE_TOKEN>` |
| **Content-Type** | `application/json` |
| **Signature header** | `X-Zyrabit-Signature: <HMAC-SHA256>` *(optional unless `N8N_REQUIRE_SIGNATURE=true`)* |

**Request body:**

```json
{
  "text": "<your natural language query>"
}
```

**Example:**

```bash
curl -X POST https://localhost/v1/integrations/n8n/webhook \
  -H "Authorization: Bearer zyrabit-service-token" \
  -H "Content-Type: application/json" \
  -d '{"text": "Summarize the onboarding process for enterprise customers."}'
```

**HMAC Signature Construction:**

When `N8N_REQUIRE_SIGNATURE=true`, compute the signature as follows and include it in the `X-Zyrabit-Signature` header:

```
HMAC-SHA256(key=N8N_WEBHOOK_SIGNING_SECRET, message=<raw request body as string>)
```

The resulting hex digest is passed as-is in the header.

---

### 4.2 Document Ingestion

| Property | Value |
|---|---|
| **Method** | `POST` |
| **Path** | `/v1/ingest` |
| **Auth header** | `Authorization: Bearer <N8N_SERVICE_TOKEN>` |

This endpoint triggers vectorization and indexing of a provided document, making it available to Zyrabit's retrieval-augmented generation pipeline.

---

## 5. Creating Your First n8n Workflow

The following section walks through building a **lead processing workflow** — a real production use case where n8n bridges an external CRM to Zyrabit to generate personalized onboarding emails from the company's internal knowledge base.

### Use Case: CRM Lead → Zyrabit → Personalized Email

When a new lead enters a CRM (e.g., HubSpot or Pipedrive), n8n sends the lead's context to Zyrabit, which queries the internal knowledge base and returns a personalized email draft. The draft is written back to the CRM record. All data remains inside the Zyrabit deployment.

---

### Step 1: Create a New Workflow

1. Open `https://localhost/n8n` in your browser.
2. Click **New workflow** in the top-right corner.
3. Name the workflow, for example: `CRM Lead → Zyrabit Onboarding Email`.

---

### Step 2: Add a Trigger Node

For a CRM-driven flow, use the **Webhook** trigger node so the CRM can push lead data to n8n:

1. Click **Add first step**.
2. Search for **Webhook** and select it.
3. Set **HTTP Method** to `POST`.
4. Note the generated webhook URL (it will be based on `https://localhost/n8n/webhook/<uuid>`).
5. Register this URL in your CRM as the new-lead webhook endpoint.

For testing purposes you may substitute the Webhook node with the **Manual Trigger** node to fire the workflow on demand from the n8n UI.

---

### Step 3: Add an HTTP Request Node (Zyrabit Inference)

This node calls `POST /v1/integrations/n8n/webhook` to query Zyrabit's RAG pipeline.

1. Click **+** after the trigger node.
2. Search for **HTTP Request** and add it.
3. Configure the node as follows:

| Field | Value |
|---|---|
| **Method** | `POST` |
| **URL** | `https://localhost/v1/integrations/n8n/webhook` |
| **Authentication** | Generic Credential Type → Header Auth |
| **Header Auth Name** | `Authorization` |
| **Header Auth Value** | `Bearer zyrabit-service-token` |
| **Body Content Type** | `JSON` |
| **Body** | See below |

**Request body (JSON):**

```json
{
  "text": "Generate a personalized onboarding email for a new enterprise lead named {{ $json.lead_name }} from {{ $json.company_name }}. Use the company's internal onboarding documentation."
}
```

The `{{ $json.lead_name }}` and `{{ $json.company_name }}` expressions reference fields from the upstream trigger node's output. Adjust field names to match your CRM's payload schema.

4. Under **Options → Response**, set **Response Format** to `JSON`.
5. Save the node.

---

### Step 4: Extract the Response

Add a **Set** node (or **Edit Fields** node) after the HTTP Request to extract the generated text from the Zyrabit response and map it to a clean output field, for example `onboarding_email_body`.

---

### Step 5: Write Back to the CRM

Add a CRM node (e.g., **HubSpot** or **Pipedrive**) to update the lead record with the generated email draft:

1. Add the relevant CRM node.
2. Configure authentication using your CRM API credentials (stored in n8n's credential manager).
3. Map the `onboarding_email_body` field to the appropriate CRM field (e.g., a note or custom property).

---

### Step 6: Activate the Workflow

1. Click **Save** in the top-right corner.
2. Toggle the **Active** switch to enable the workflow.
3. The workflow will now trigger automatically whenever the CRM posts a new lead to the registered webhook URL.

---

## 6. Document Ingestion Automation Workflow

This workflow monitors a shared folder for new PDF uploads and automatically ingests them into Zyrabit's vector store, making their content immediately available to the RAG pipeline.

### Use Case: Shared Folder → Zyrabit Vector Store

When a new PDF is written to a watched directory (e.g., via a network share, S3 bucket, or FTP), n8n detects the new file and calls `POST /v1/ingest` to vectorize it.

---

### Workflow Steps

**1. Trigger: Schedule or File Watcher**

Use the **Schedule** trigger node to poll for new files at a defined interval (e.g., every 5 minutes), or use an **FTP** / **S3** node with event-driven triggering if your storage backend supports it.

**2. Read File**

Use the **Read Binary File** node to read the file from disk, or the appropriate cloud storage node (e.g., **AWS S3**) to download the file content.

**3. HTTP Request Node (Ingest)**

Add an HTTP Request node configured as follows:

| Field | Value |
|---|---|
| **Method** | `POST` |
| **URL** | `https://localhost/v1/ingest` |
| **Authentication** | Generic Credential Type → Header Auth |
| **Header Auth Name** | `Authorization` |
| **Header Auth Value** | `Bearer zyrabit-service-token` |
| **Body Content Type** | `Binary` |
| **Binary Property** | Name of the binary field from the Read File node |

**4. Log Result**

Add a **Set** node or send a notification (e.g., Slack, email) to log whether the ingestion succeeded or failed, using the HTTP status code returned by `api-rag`.

---

## 7. Security Considerations

### Service Token Rotation

The `N8N_SERVICE_TOKEN` grants unrestricted access to the `api-rag` integration endpoints. Treat it as a high-privilege credential:

- Rotate the token periodically and update it in both `.env` (or Docker Secrets) and n8n's credential store.
- Use a unique token per integration environment (development, staging, production).
- Never log the token value in n8n workflow outputs.

### HMAC Signature Verification

Setting `N8N_REQUIRE_SIGNATURE=true` in `.env` enables mandatory request signature verification on `api-rag`. When enabled:

1. n8n must compute `HMAC-SHA256(N8N_WEBHOOK_SIGNING_SECRET, <raw JSON body>)` and include the hex digest in the `X-Zyrabit-Signature` request header.
2. `api-rag` rejects any request where the signature is absent or does not match.

This provides a second layer of defense beyond the bearer token, preventing replayed or forged requests from reaching the inference pipeline.

:::important
Enabling `N8N_REQUIRE_SIGNATURE=true` requires that n8n's HTTP Request node is configured with a **Code** node upstream that computes and injects the `X-Zyrabit-Signature` header. Use n8n's built-in `$jsfunc` crypto helpers or a **Code** node with the Node.js `crypto` module to generate the HMAC digest.
:::

### Network Isolation

`zyrabit-n8n` is attached exclusively to `zyrabit-sovereign-net`. It has no direct external network egress beyond what Traefik exposes. Ensure that no additional networks are attached to the container in custom deployments, and that Traefik's routing rules restrict `/n8n` access to authorized clients only (e.g., via IP allowlisting at the Traefik middleware layer).

### Persistent Volume Permissions

The `./n8n-data` volume stores workflow definitions, credentials, and execution history in plaintext on the host filesystem. Apply appropriate filesystem permissions:

```bash
chmod 700 ./n8n-data
chown 1000:1000 ./n8n-data  # n8n runs as UID 1000 inside the container
```

### Cookie Security

`N8N_SECURE_COOKIE=false` is set to accommodate local TLS with self-signed certificates. In a production environment served over a properly trusted HTTPS certificate, set this to `true` to ensure session cookies are transmitted only over encrypted connections.

---

## 8. Quick Reference

| Item | Value |
|---|---|
| n8n Docker image | `n8nio/n8n:1.50.0` |
| Container name | `zyrabit-n8n` |
| Compose profile | `automation` |
| Internal port | `5678` |
| UI URL | `https://localhost/n8n` |
| Webhook base URL | `https://localhost/n8n/` |
| Inference endpoint | `POST /v1/integrations/n8n/webhook` |
| Ingestion endpoint | `POST /v1/ingest` |
| Auth header | `Authorization: Bearer <N8N_SERVICE_TOKEN>` |
| Signature header | `X-Zyrabit-Signature: <HMAC-SHA256 hex>` |
| Signature algorithm | HMAC SHA-256 |
| Signature enforcement | `N8N_REQUIRE_SIGNATURE` (default: `false`) |
| Data volume | `./n8n-data:/home/node/.n8n` |
| Docker network | `zyrabit-sovereign-net` |
